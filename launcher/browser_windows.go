// This file is part of PSMemoryManager.
// SPDX-License-Identifier: GPL-3.0-or-later

//go:build windows

package main

import (
	"fmt"
	"os/exec"
	"syscall"
)

// on Windows the app runs in a console window: closing it also quits
const quitHint = "Close this window to quit. / Feche esta janela para sair."

// openBrowser opens url in the default browser (the same call Explorer uses for links).
func openBrowser(url string) {
	c := exec.Command("rundll32", "url.dll,FileProtocolHandler", url)
	c.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}
	if err := c.Start(); err != nil {
		fmt.Println("Could not open the browser; open the address above. / Não deu para abrir o navegador; abra o endereço acima.")
		return
	}
	go c.Wait() // reap it
}
