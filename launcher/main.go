// This file is part of PSMemoryManager.
// SPDX-License-Identifier: GPL-3.0-or-later

// PSMemoryManager local app: one executable with the whole web page inside
// (Pyodide included). It serves the page on this computer only (127.0.0.1),
// opens the browser, and quits a little after the last tab is closed.
// Nothing is installed and nothing needs the internet.
//
// Build it with tools/build_local.py, which puts the gzipped site in site/.
package main

import (
	"bytes"
	"compress/gzip"
	"context"
	"embed"
	"errors"
	"flag"
	"fmt"
	"io"
	"io/fs"
	"mime"
	"net"
	"net/http"
	"os"
	"path"
	"strconv"
	"strings"
	"sync"
	"time"
)

//go:embed all:site
var embedded embed.FS

// set at build time: -ldflags "-X main.version=..."
var version = "dev"

const (
	defaultPort = 47820 // fixed, so the browser keeps the language/theme between runs
	pingPath    = "/__psmm/ping"
	alivePath   = "/__psmm/alive"
	scriptPath  = "/__psmm/local.js"
	pingReply   = "PSMemoryManager"
	firstWait   = 5 * time.Minute  // no tab ever connected (browser did not open)
	closeGrace  = 45 * time.Second // after the last tab is gone (covers reloads)
)

// Script added to the page: keeps a connection open while the tab is open,
// and explains what happened if the app was closed.
const localScript = `(() => {
  const pt = (navigator.language || "").toLowerCase().startsWith("pt");
  let bar = null, fails = 0;
  const show = () => {
    if (bar) return;
    bar = document.createElement("div");
    bar.setAttribute("role", "status");
    bar.style.cssText = "position:fixed;left:50%;bottom:44px;transform:translateX(-50%);z-index:9999;max-width:min(560px,calc(100vw - 32px));padding:10px 14px;border-radius:8px;background:#b42318;color:#fff;font:14px/1.4 system-ui,sans-serif;box-shadow:0 4px 16px rgba(0,0,0,.25)";
    bar.textContent = pt
      ? "O aplicativo PSMemoryManager foi fechado. O que está aberto continua funcionando, mas para recarregar a página abra o aplicativo de novo."
      : "The PSMemoryManager app was closed. What is open keeps working, but to reload the page open the app again.";
    document.body.appendChild(bar);
  };
  const es = new EventSource("__psmm/alive");
  es.onopen = () => { fails = 0; if (bar) { bar.remove(); bar = null; } };
  es.onerror = () => { if (++fails >= 2) show(); };
})();
`

type server struct {
	site  fs.FS
	build string // ETag for every file: changes with each build
	port  int

	mu       sync.Mutex
	tabs     int
	lastSeen time.Time
	everSeen bool
}

func main() {
	port := flag.Int("port", defaultPort, "port on 127.0.0.1 (another free port is used if it is taken)")
	noBrowser := flag.Bool("no-browser", false, "do not open the browser")
	showVersion := flag.Bool("version", false, "print the version and exit")
	flag.Parse()
	if *showVersion {
		fmt.Println("PSMemoryManager", version)
		return
	}

	site, err := fs.Sub(embedded, "site")
	if err != nil {
		fail(err)
	}
	s := &server{site: site, build: readBuild(site), lastSeen: time.Now()}

	ln, err := net.Listen("tcp", net.JoinHostPort("127.0.0.1", strconv.Itoa(*port)))
	if err != nil {
		// already open? then just show it again
		if isOurs(*port) {
			url := fmt.Sprintf("http://127.0.0.1:%d/", *port)
			fmt.Println("PSMemoryManager is already running:", url)
			if !*noBrowser {
				openBrowser(url)
			}
			return
		}
		if ln, err = net.Listen("tcp", "127.0.0.1:0"); err != nil {
			fail(err)
		}
	}
	s.port = ln.Addr().(*net.TCPAddr).Port
	url := fmt.Sprintf("http://127.0.0.1:%d/", s.port)

	fmt.Printf("PSMemoryManager %s\n", version)
	fmt.Println("Open in your browser / Abra no navegador:", url)
	fmt.Println("It closes by itself shortly after you close its browser tab (or press Ctrl+C).")
	fmt.Println("Fecha sozinho logo depois que você fechar a aba do navegador (ou aperte Ctrl+C).")

	srv := &http.Server{Handler: s, ReadHeaderTimeout: 10 * time.Second}
	go s.watch(srv)
	if !*noBrowser {
		openBrowser(url)
	}
	if err := srv.Serve(ln); err != nil && !errors.Is(err, http.ErrServerClosed) {
		fail(err)
	}
}

func fail(err error) {
	fmt.Fprintln(os.Stderr, "PSMemoryManager:", err)
	os.Exit(1)
}

func readBuild(site fs.FS) string {
	data, err := readFile(site, "version.json")
	if err != nil {
		return version
	}
	return strconv.FormatUint(uint64(fnv32(data)), 16)
}

func fnv32(b []byte) uint32 {
	h := uint32(2166136261)
	for _, c := range b {
		h = (h ^ uint32(c)) * 16777619
	}
	return h
}

// isOurs tells whether PSMemoryManager is the one using the port.
func isOurs(port int) bool {
	c := http.Client{Timeout: 2 * time.Second}
	r, err := c.Get(fmt.Sprintf("http://127.0.0.1:%d%s", port, pingPath))
	if err != nil {
		return false
	}
	defer r.Body.Close()
	b, _ := io.ReadAll(io.LimitReader(r.Body, 64))
	return string(b) == pingReply
}

// watch quits when no tab has been connected for a while.
func (s *server) watch(srv *http.Server) {
	for range time.Tick(2 * time.Second) {
		s.mu.Lock()
		idle := s.tabs == 0 && time.Since(s.lastSeen) > map[bool]time.Duration{true: closeGrace, false: firstWait}[s.everSeen]
		s.mu.Unlock()
		if idle {
			fmt.Println("No open tab: closing. / Nenhuma aba aberta: fechando.")
			ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
			_ = srv.Shutdown(ctx)
			cancel()
			os.Exit(0)
		}
	}
}

func (s *server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	// only this computer, and only under our own address (blocks DNS rebinding)
	host := r.Host
	if h, p, err := net.SplitHostPort(host); err != nil || p != strconv.Itoa(s.port) || (h != "127.0.0.1" && h != "localhost") {
		http.Error(w, "forbidden", http.StatusForbidden)
		return
	}
	if r.Method != http.MethodGet && r.Method != http.MethodHead {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.Header().Set("Referrer-Policy", "no-referrer")

	switch r.URL.Path {
	case pingPath:
		io.WriteString(w, pingReply)
		return
	case alivePath:
		s.alive(w, r)
		return
	case scriptPath:
		w.Header().Set("Content-Type", "text/javascript; charset=utf-8")
		w.Header().Set("Cache-Control", "no-cache")
		io.WriteString(w, localScript)
		return
	}

	name := strings.TrimPrefix(path.Clean("/"+r.URL.Path), "/")
	if name == "" {
		name = "index.html"
	}
	if name == "index.html" {
		s.index(w, r)
		return
	}
	s.file(w, r, name)
}

// alive is held open by each tab (Server-Sent Events) until the tab closes.
func (s *server) alive(w http.ResponseWriter, r *http.Request) {
	fl, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "streaming unsupported", http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-store")
	s.mu.Lock()
	s.tabs++
	s.everSeen = true
	s.mu.Unlock()
	defer func() {
		s.mu.Lock()
		s.tabs--
		s.lastSeen = time.Now()
		s.mu.Unlock()
	}()
	io.WriteString(w, "retry: 2000\n\n")
	fl.Flush()
	t := time.NewTicker(20 * time.Second)
	defer t.Stop()
	for {
		select {
		case <-r.Context().Done():
			return
		case <-t.C:
			if _, err := io.WriteString(w, ": keep-alive\n\n"); err != nil {
				return
			}
			fl.Flush()
		}
	}
}

// index serves the page with the local-app script added.
func (s *server) index(w http.ResponseWriter, r *http.Request) {
	page, err := readFile(s.site, "index.html")
	if err != nil {
		http.Error(w, "page missing", http.StatusInternalServerError)
		return
	}
	tag := []byte(`<script src="__psmm/local.js"></script></body>`)
	page = bytes.Replace(page, []byte("</body>"), tag, 1)
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Header().Set("Cache-Control", "no-cache")
	w.Write(page)
}

// file serves an embedded file, gzipped as stored when the browser accepts it.
func (s *server) file(w http.ResponseWriter, r *http.Request, name string) {
	gz, err := fs.ReadFile(s.site, name+".gz")
	if err != nil {
		http.NotFound(w, r)
		return
	}
	ctype := mime.TypeByExtension(path.Ext(name))
	if ctype == "" {
		ctype = "application/octet-stream"
	}
	etag := `"` + s.build + `"`
	w.Header().Set("Content-Type", ctype)
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("ETag", etag)
	w.Header().Set("Vary", "Accept-Encoding")
	if r.Header.Get("If-None-Match") == etag {
		w.WriteHeader(http.StatusNotModified)
		return
	}
	if strings.Contains(r.Header.Get("Accept-Encoding"), "gzip") {
		w.Header().Set("Content-Encoding", "gzip")
		w.Header().Set("Content-Length", strconv.Itoa(len(gz)))
		if r.Method != http.MethodHead {
			w.Write(gz)
		}
		return
	}
	data, err := gunzip(gz)
	if err != nil {
		http.Error(w, "damaged file", http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Length", strconv.Itoa(len(data)))
	if r.Method != http.MethodHead {
		w.Write(data)
	}
}

func readFile(site fs.FS, name string) ([]byte, error) {
	gz, err := fs.ReadFile(site, name+".gz")
	if err != nil {
		return nil, err
	}
	return gunzip(gz)
}

func gunzip(b []byte) ([]byte, error) {
	zr, err := gzip.NewReader(bytes.NewReader(b))
	if err != nil {
		return nil, err
	}
	defer zr.Close()
	return io.ReadAll(zr)
}

func init() {
	// not in every system's MIME table (Windows reads it from the registry)
	for ext, t := range map[string]string{
		".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
		".css": "text/css; charset=utf-8", ".json": "application/json", ".wasm": "application/wasm",
		".svg": "image/svg+xml", ".png": "image/png", ".zip": "application/zip", ".whl": "application/zip",
		".txt": "text/plain; charset=utf-8", ".py": "text/plain; charset=utf-8",
	} {
		_ = mime.AddExtensionType(ext, t)
	}
}
