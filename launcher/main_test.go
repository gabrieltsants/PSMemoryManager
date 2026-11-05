// This file is part of PSMemoryManager.
// SPDX-License-Identifier: GPL-3.0-or-later

package main

import (
	"bytes"
	"compress/gzip"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"testing/fstest"
)

func gz(t *testing.T, s string) []byte {
	var b bytes.Buffer
	w := gzip.NewWriter(&b)
	w.Write([]byte(s))
	w.Close()
	return b.Bytes()
}

func testServer(t *testing.T) *server {
	return &server{
		site: fstest.MapFS{
			"index.html.gz":               {Data: gz(t, "<html><body>hi</body></html>")},
			"app.js.gz":                   {Data: gz(t, "console.log(1)")},
			"pyodide/pyodide.asm.wasm.gz": {Data: gz(t, "\x00asm")},
		},
		build: "b1",
		port:  4321,
	}
}

func get(s *server, host, target string, hdr map[string]string) *httptest.ResponseRecorder {
	r := httptest.NewRequest(http.MethodGet, target, nil)
	r.Host = host
	for k, v := range hdr {
		r.Header.Set(k, v)
	}
	w := httptest.NewRecorder()
	s.ServeHTTP(w, r)
	return w
}

func TestOnlyOwnHost(t *testing.T) {
	s := testServer(t)
	for _, host := range []string{"evil.example:4321", "127.0.0.1:9999", "192.168.0.2:4321", "127.0.0.1"} {
		if c := get(s, host, "/", nil).Code; c != http.StatusForbidden {
			t.Errorf("host %q: got %d, want 403", host, c)
		}
	}
	for _, host := range []string{"127.0.0.1:4321", "localhost:4321"} {
		if c := get(s, host, "/", nil).Code; c != http.StatusOK {
			t.Errorf("host %q: got %d, want 200", host, c)
		}
	}
}

func TestIndexGetsLocalScript(t *testing.T) {
	w := get(testServer(t), "127.0.0.1:4321", "/", nil)
	if !strings.Contains(w.Body.String(), `<script src="__psmm/local.js"></script></body>`) {
		t.Fatalf("script not added: %q", w.Body.String())
	}
}

func TestFilesGzipOrPlain(t *testing.T) {
	s := testServer(t)
	w := get(s, "127.0.0.1:4321", "/pyodide/pyodide.asm.wasm", map[string]string{"Accept-Encoding": "gzip, br"})
	if w.Header().Get("Content-Encoding") != "gzip" || w.Header().Get("Content-Type") != "application/wasm" {
		t.Fatalf("headers: %v", w.Header())
	}
	w = get(s, "127.0.0.1:4321", "/app.js", nil)
	if w.Body.String() != "console.log(1)" || w.Header().Get("Content-Encoding") != "" {
		t.Fatalf("plain: %q %v", w.Body.String(), w.Header())
	}
	if c := get(s, "127.0.0.1:4321", "/app.js", map[string]string{"If-None-Match": `"b1"`}).Code; c != http.StatusNotModified {
		t.Fatalf("etag: got %d", c)
	}
}

func TestNotFoundAndTraversal(t *testing.T) {
	s := testServer(t)
	for _, p := range []string{"/missing.js", "/../index.html.gz", "/pyodide/", "/app.js.gz"} {
		if c := get(s, "127.0.0.1:4321", p, nil).Code; c != http.StatusNotFound {
			t.Errorf("%s: got %d, want 404", p, c)
		}
	}
}

func TestPing(t *testing.T) {
	if b := get(testServer(t), "127.0.0.1:4321", pingPath, nil).Body.String(); b != pingReply {
		t.Fatalf("ping: %q", b)
	}
}
