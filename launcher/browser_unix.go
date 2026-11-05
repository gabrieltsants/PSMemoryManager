// This file is part of PSMemoryManager.
// SPDX-License-Identifier: GPL-3.0-or-later

//go:build !windows

package main

import (
	"fmt"
	"os/exec"
	"runtime"
)

// openBrowser opens url in the default browser (xdg-open on Linux, open on macOS).
func openBrowser(url string) {
	cmd := "xdg-open"
	if runtime.GOOS == "darwin" {
		cmd = "open"
	}
	c := exec.Command(cmd, url)
	if err := c.Start(); err != nil {
		fmt.Println("Could not open the browser; open the address above. / Não deu para abrir o navegador; abra o endereço acima.")
		return
	}
	go c.Wait() // reap it
}
