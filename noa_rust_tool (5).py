#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOA RUST TOOL
Тактическая утилита клана NOA (NeNormal / Omperial / Anarchy's)
Модули: RAM CHECK + OPTIMIZATION
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import sys
import platform
import ctypes
import os
import re

try:
    import winreg
except ImportError:
    winreg = None

# ============================================================
#   ЦВЕТОВАЯ СХЕМА  —  "холодный / милитаристский / серьёзный"
# ============================================================
COL_BG        = "#0a0a0a"
COL_PANEL     = "#111111"
COL_PANEL_2   = "#161616"
COL_BORDER    = "#2a2a2a"
COL_RED       = "#c81d25"
COL_RED_DARK  = "#7a1216"
COL_RED_DIM   = "#3a1013"
COL_TEXT      = "#d8d8d8"
COL_TEXT_DIM  = "#7d7d7d"
COL_GREEN     = "#3fae4a"
COL_YELLOW    = "#c8961d"
COL_WHITE     = "#f0f0f0"

FONT_MONO   = ("Consolas", 10)
FONT_MONO_B = ("Consolas", 10, "bold")
FONT_TITLE  = ("Consolas", 15, "bold")
FONT_TAB    = ("Consolas", 10, "bold")
FONT_SMALL  = ("Consolas", 9)
FONT_HEAD   = ("Consolas", 11, "bold")


# ============================================================
#   POWERSHELL СКРИПТ ДЛЯ СБОРА ДАННЫХ О ПАМЯТИ
# ============================================================
PS_RAM_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
try {
    $ram = Get-CimInstance Win32_PhysicalMemory
    $os  = Get-CimInstance Win32_OperatingSystem
    $cs  = Get-CimInstance Win32_ComputerSystem
} catch {
    Write-Output "ERROR|$($_.Exception.Message)"
    exit 1
}

if (-not $ram) {
    Write-Output "ERROR|Modules not found"
    exit 1
}

$totalGB   = [math]::Round(($ram | Measure-Object Capacity -Sum).Sum / 1GB, 1)
$count     = $ram.Count
$slotsUsed = $count
$slotsMax  = 0
try {
    $arr = Get-CimInstance Win32_PhysicalMemoryArray
    if ($arr) { $slotsMax = ($arr | Measure-Object MemoryDevices -Sum).Sum }
} catch {}
if (-not $slotsMax -or $slotsMax -lt $slotsUsed) { $slotsMax = $slotsUsed }

$freeGB = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
$usedGB = [math]::Round($totalGB - $freeGB, 1)
$loadPct = [math]::Round((($totalGB - $freeGB) / $totalGB) * 100, 0)

Write-Output "SUMMARY|$totalGB|$count|$slotsUsed|$slotsMax|$usedGB|$freeGB|$loadPct"

foreach ($m in $ram) {
    $man = if ($m.Manufacturer) { $m.Manufacturer.Trim() } else { 'N/A' }
    $part = if ($m.PartNumber) { $m.PartNumber.Trim() } else { 'N/A' }
    $type = switch ($m.SMBIOSMemoryType) { 24 {'DDR3'} 26 {'DDR4'} 30 {'DDR5'} default {'UNKNOWN'} }
    $speed = if ($m.Speed) { $m.Speed } else { 0 }
    $cur   = if ($m.ConfiguredClockSpeed) { $m.ConfiguredClockSpeed } else { 0 }
    $cap   = [math]::Round($m.Capacity / 1GB, 0)
    $slot  = if ($m.DeviceLocator) { $m.DeviceLocator.Trim() } else { 'N/A' }
    $volt  = if ($m.ConfiguredVoltage) { $m.ConfiguredVoltage } else { 0 }
    $serial = if ($m.SerialNumber) { $m.SerialNumber.Trim() } else { 'N/A' }
    $ff = switch ($m.FormFactor) { 8 {'DIMM'} 12 {'SO-DIMM'} default {'N/A'} }
    Write-Output "MODULE|$man|$part|$type|$speed|$cur|$cap|$slot|$volt|$serial|$ff"
}
"""


def run_ram_check():
    system = platform.system()
    if system != "Windows":
        return {"error": "Диагностика доступна только на Windows (WMI/CIM)."}

    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", PS_RAM_SCRIPT],
            capture_output=True, text=True, timeout=25,
            startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception as e:
        return {"error": f"Не удалось запустить PowerShell: {e}"}

    out = proc.stdout.strip()
    if not out:
        return {"error": proc.stderr.strip() or "Пустой ответ от системы."}

    result = {"summary": None, "modules": []}
    for line in out.splitlines():
        parts = line.split("|")
        if not parts:
            continue
        tag = parts[0]
        if tag == "ERROR":
            return {"error": parts[1] if len(parts) > 1 else "Неизвестная ошибка."}
        elif tag == "SUMMARY":
            result["summary"] = {
                "total_gb": parts[1], "count": parts[2],
                "slots_used": parts[3], "slots_max": parts[4],
                "used_gb": parts[5], "free_gb": parts[6], "load_pct": parts[7],
            }
        elif tag == "MODULE":
            result["modules"].append({
                "manufacturer": parts[1], "part": parts[2], "type": parts[3],
                "speed": int(parts[4]), "current": int(parts[5]), "cap": parts[6],
                "slot": parts[7], "voltage": parts[8], "serial": parts[9], "form": parts[10],
            })
    return result


def add_hover(button, normal_bg, hover_bg, normal_fg=None, hover_fg=None):
    """Добавляет плавную подсветку кнопки при наведении мыши."""
    def on_enter(e):
        button.config(bg=hover_bg)
        if hover_fg:
            button.config(fg=hover_fg)

    def on_leave(e):
        button.config(bg=normal_bg)
        if normal_fg:
            button.config(fg=normal_fg)

    button.bind("<Enter>", on_enter)
    button.bind("<Leave>", on_leave)


def ru_plural(n, one, few, many):
    """Корректное склонение русских числительных: 1 модуль, 2 модуля, 5 модулей."""
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return few
    return many


def _run_ps(cmd, timeout=15):
    if platform.system() != "Windows":
        return False, "", "Только Windows"
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        p = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
            capture_output=True, text=True, timeout=timeout,
            startupinfo=si, creationflags=subprocess.CREATE_NO_WINDOW
        )
        return p.returncode == 0, p.stdout.strip(), p.stderr.strip()
    except Exception as e:
        return False, "", str(e)


def _run_cmd(args, timeout=15):
    if platform.system() != "Windows":
        return False, "", "Только Windows"
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        p = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout,
            startupinfo=si, creationflags=subprocess.CREATE_NO_WINDOW
        )
        return p.returncode == 0, p.stdout.strip(), p.stderr.strip()
    except Exception as e:
        return False, "", str(e)


# ============================================================
#   ВИДЖЕТ: КНОПКА-ВКЛАДКА
# ============================================================
class TabButton(tk.Frame):
    def __init__(self, master, text, command, active=False, **kw):
        super().__init__(master, bg=COL_BG, **kw)
        self.command = command
        self.active = active

        self.bar = tk.Frame(self, bg=COL_RED if active else COL_BG, height=2)
        self.bar.pack(side="top", fill="x")

        self.lbl = tk.Label(
            self, text=text, font=FONT_TAB,
            bg=COL_PANEL if active else COL_BG,
            fg=COL_WHITE if active else COL_TEXT_DIM,
            padx=14, pady=7, cursor="hand2"
        )
        self.lbl.pack(side="top", fill="x")

        for w in (self, self.lbl):
            w.bind("<Button-1>", lambda e: self.command())
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

    def _on_enter(self, e):
        if not self.active:
            self.lbl.config(fg=COL_RED)

    def _on_leave(self, e):
        if not self.active:
            self.lbl.config(fg=COL_TEXT_DIM)

    def set_active(self, active):
        self.active = active
        self.bar.config(bg=COL_RED if active else COL_BG)
        self.lbl.config(
            bg=COL_PANEL if active else COL_BG,
            fg=COL_WHITE if active else COL_TEXT_DIM
        )


# ============================================================
#   ВИДЖЕТ: ПЕРЕКЛЮЧАТЕЛЬ ON/OFF (плавная анимация)
# ============================================================
class ToggleSwitch(tk.Canvas):
    """Pill-переключатель с плавным слайдом. ON = зелёный, OFF = красный."""

    WIDTH = 72
    HEIGHT = 28
    PAD = 3
    KNOB = 22
    STEPS = 12
    DELAY = 12

    def __init__(self, master, command=None, **kw):
        super().__init__(
            master, width=self.WIDTH, height=self.HEIGHT,
            bg=COL_PANEL_2, highlightthickness=0, bd=0, **kw
        )
        self.command = command
        self._state = False
        self._busy = False
        self._animating = False
        self._progress = 0.0
        self.bind("<Button-1>", self._toggle)
        self._draw(self._progress)

    def get(self):
        return self._state

    def set(self, value, trigger=False):
        value = bool(value)
        if value == self._state and not trigger:
            self._progress = 1.0 if value else 0.0
            self._draw(self._progress)
            return
        self._state = value
        if trigger:
            self._animate_to(1.0 if value else 0.0, then_cmd=True)
        else:
            self._progress = 1.0 if value else 0.0
            self._draw(self._progress)

    def _toggle(self, event=None):
        if self._busy or self._animating:
            return
        self._state = not self._state
        self._animate_to(1.0 if self._state else 0.0, then_cmd=True)

    def _animate_to(self, target, then_cmd=False):
        if self._animating:
            return
        self._animating = True
        start = self._progress
        delta = target - start
        step = [0]

        def frame():
            step[0] += 1
            t = step[0] / self.STEPS
            # ease-out cubic — плавное замедление в конце
            t = 1 - (1 - t) ** 3
            self._progress = start + delta * t
            self._draw(self._progress)
            if step[0] < self.STEPS:
                self.after(self.DELAY, frame)
            else:
                self._progress = target
                self._draw(self._progress)
                self._animating = False
                if then_cmd and self.command:
                    self.command(self._state)

        frame()

    def _lerp_color(self, c1, c2, t):
        def hex_to_rgb(h):
            h = h.lstrip("#")
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        r1, g1, b1 = hex_to_rgb(c1)
        r2, g2, b2 = hex_to_rgb(c2)
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _draw(self, progress):
        self.delete("all")
        w, h = self.WIDTH, self.HEIGHT
        r = h // 2
        t = max(0.0, min(1.0, progress))

        bg = self._lerp_color("#e74c3c", "#2ecc40", t)

        self.create_oval(0, 0, h, h, fill=bg, outline="")
        self.create_oval(w - h, 0, w, h, fill=bg, outline="")
        self.create_rectangle(r, 0, w - r, h, fill=bg, outline="")

        if t < 0.55:
            alpha = max(0.0, 1.0 - t * 2.2)
            gray = int(180 + 75 * alpha)
            self.create_text(
                w - 20, h // 2, text="OFF",
                fill=f"#{gray:02x}{gray:02x}{gray:02x}",
                font=("Consolas", 9, "bold"), anchor="center"
            )
        if t > 0.45:
            alpha = max(0.0, (t - 0.45) * 2.2)
            gray = int(180 + 75 * min(1.0, alpha))
            self.create_text(
                18, h // 2, text="ON",
                fill=f"#{gray:02x}{gray:02x}{gray:02x}",
                font=("Consolas", 9, "bold"), anchor="center"
            )

        kr = self.KNOB // 2
        x_off = self.PAD + kr + 1
        x_on = w - self.PAD - kr - 1
        knob_x = x_off + (x_on - x_off) * t

        self.create_oval(
            knob_x - kr, h // 2 - kr,
            knob_x + kr, h // 2 + kr,
            fill="#f5f5f5", outline="#dddddd"
        )



# ============================================================
#   ГЛАВНОЕ ПРИЛОЖЕНИЕ
# ============================================================
class NoaRustTool(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("N O A   R U S T   T O O L")
        self.geometry("1280x720")
        self.resizable(True, True)
        self.minsize(1100, 650)
        self.configure(bg=COL_BG)

        try:
            self.iconbitmap(default="")
        except Exception:
            pass

        self.opt_backup = {}
        self.opt_vars = {}
        self.opt_status_lbls = {}
        self.opt_cards = {}

        self._build_header()
        self._build_tabbar()
        self._build_body()

        self.tabs = {}
        self._register_tab("ram", "RAM CHECK", self._build_ram_tab)
        self._register_tab("opt", "OPTIMIZATION", self._build_opt_tab)

        self._show_tab("ram")
        self.after(400, self._refresh_all_opt_status)

    def _is_admin(self):
        if platform.system() != "Windows":
            return None
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return None

    def _build_header(self):
        header = tk.Frame(self, bg=COL_BG, height=58)
        header.pack(side="top", fill="x")
        header.pack_propagate(False)

        left = tk.Frame(header, bg=COL_BG)
        left.pack(side="left", padx=16, pady=8)

        tk.Label(left, text="N", font=("Consolas", 20, "bold"),
                 bg=COL_BG, fg=COL_RED).pack(side="left")
        tk.Label(left, text="OA", font=("Consolas", 20, "bold"),
                 bg=COL_BG, fg=COL_WHITE).pack(side="left")
        tk.Label(left, text="  RUST TOOL", font=("Consolas", 13),
                 bg=COL_BG, fg=COL_TEXT_DIM).pack(side="left", padx=(6, 0))

        # Пилюля статуса прав администратора — функциональна и визуально заметна
        is_admin = self._is_admin()
        if is_admin is True:
            pill_text, pill_fg = "\u25cf ADMIN", COL_GREEN
        elif is_admin is False:
            pill_text, pill_fg = "\u25cf USER (ограничено)", COL_YELLOW
        else:
            pill_text, pill_fg = "\u25cf N/A", COL_TEXT_DIM

        pill = tk.Frame(left, bg=COL_PANEL_2, highlightbackground=COL_BORDER, highlightthickness=1)
        pill.pack(side="left", padx=(14, 0))
        tk.Label(pill, text=pill_text, font=("Consolas", 8, "bold"),
                 bg=COL_PANEL_2, fg=pill_fg, padx=8, pady=3).pack()

        right = tk.Frame(header, bg=COL_BG)
        right.pack(side="right", padx=16)
        tk.Label(right, text="NeNormal \u2022 Omperial \u2022 Anarchy's",
                 font=("Consolas", 8), bg=COL_BG, fg=COL_RED_DARK).pack(anchor="e")
        tk.Label(right, text="TACTICAL CONFIG SUITE  v2.0",
                 font=("Consolas", 8), bg=COL_BG, fg=COL_TEXT_DIM).pack(anchor="e")

        sep = tk.Frame(self, bg=COL_RED_DARK, height=1)
        sep.pack(side="top", fill="x")
        glow = tk.Frame(self, bg=COL_RED_DIM, height=1)
        glow.pack(side="top", fill="x")

    def _build_tabbar(self):
        bar = tk.Frame(self, bg=COL_BG, height=38)
        bar.pack(side="top", fill="x")
        bar.pack_propagate(False)

        self.tab_bar_left = tk.Frame(bar, bg=COL_BG)
        self.tab_bar_left.pack(side="left", padx=16, pady=(6, 0))

        sep = tk.Frame(self, bg=COL_BORDER, height=1)
        sep.pack(side="top", fill="x")

    def _build_body(self):
        self.body = tk.Frame(self, bg=COL_BG)
        self.body.pack(side="top", fill="both", expand=True)

    def _register_tab(self, key, label, builder_fn):
        btn = TabButton(self.tab_bar_left, label, lambda k=key: self._show_tab(k))
        btn.pack(side="left", padx=(0, 4))
        frame = tk.Frame(self.body, bg=COL_BG)
        builder_fn(frame)
        self.tabs[key] = {"button": btn, "frame": frame}

    def _show_tab(self, key):
        for k, t in self.tabs.items():
            if k == key:
                t["button"].set_active(True)
                t["frame"].place(x=0, y=0, relwidth=1, relheight=1)
                t["frame"].tkraise()
            else:
                t["button"].set_active(False)
                t["frame"].place_forget()
        if key == "opt":
            self.after(150, self._refresh_all_opt_status)

    # ===========================================================
    #   ВКЛАДКА: RAM CHECK
    # ===========================================================
    def _build_ram_tab(self, parent):
        top = tk.Frame(parent, bg=COL_BG)
        top.pack(side="top", fill="x", padx=16, pady=(12, 6))

        tk.Label(top, text="ДИАГНОСТИКА ОПЕРАТИВНОЙ ПАМЯТИ",
                 font=FONT_HEAD, bg=COL_BG, fg=COL_WHITE).pack(side="left")

        self.ram_status_lbl = tk.Label(top, text="\u25cf ОЖИДАНИЕ", font=FONT_SMALL,
                                        bg=COL_BG, fg=COL_TEXT_DIM)
        self.ram_status_lbl.pack(side="right")

        btn_frame = tk.Frame(parent, bg=COL_BG)
        btn_frame.pack(side="top", fill="x", padx=16, pady=(0, 10))

        self.scan_btn = tk.Button(
            btn_frame, text="\u25b6  ЗАПУСТИТЬ СКАНИРОВАНИЕ", font=FONT_MONO_B,
            bg=COL_RED, fg=COL_WHITE, activebackground=COL_RED_DARK,
            activeforeground=COL_WHITE, relief="flat", bd=0, padx=14, pady=8,
            cursor="hand2", command=self._start_ram_scan
        )
        self.scan_btn.pack(side="left")
        add_hover(self.scan_btn, COL_RED, COL_RED_DARK)

        self.copy_btn = tk.Button(
            btn_frame, text="КОПИРОВАТЬ ОТЧЁТ", font=FONT_MONO, bg=COL_PANEL_2,
            fg=COL_TEXT_DIM, activebackground=COL_PANEL_2, activeforeground=COL_WHITE,
            relief="flat", bd=0, padx=12, pady=8, cursor="hand2",
            command=self._copy_report, state="disabled"
        )
        self.copy_btn.pack(side="left", padx=(8, 0))
        add_hover(self.copy_btn, COL_PANEL_2, COL_BORDER, COL_TEXT_DIM, COL_WHITE)

        self.summary_frame = tk.Frame(parent, bg=COL_PANEL, highlightbackground=COL_BORDER,
                                       highlightthickness=1)
        self.summary_frame.pack(side="top", fill="x", padx=16, pady=(0, 10))
        self._build_summary_placeholder()

        out_wrap = tk.Frame(parent, bg=COL_PANEL, highlightbackground=COL_BORDER,
                             highlightthickness=1)
        out_wrap.pack(side="top", fill="both", expand=True, padx=16, pady=(0, 14))

        out_head = tk.Frame(out_wrap, bg=COL_PANEL_2, height=26)
        out_head.pack(side="top", fill="x")
        out_head.pack_propagate(False)
        tk.Label(out_head, text="ОТЧЁТ ПО МОДУЛЯМ", font=FONT_SMALL,
                 bg=COL_PANEL_2, fg=COL_RED).pack(side="left", padx=10)

        canvas_frame = tk.Frame(out_wrap, bg=COL_PANEL)
        canvas_frame.pack(side="top", fill="both", expand=True, padx=1, pady=1)

        scrollbar = tk.Scrollbar(canvas_frame, bg=COL_PANEL, troughcolor=COL_BG,
                                  activebackground=COL_RED_DARK)
        scrollbar.pack(side="right", fill="y")

        self.ram_canvas = tk.Canvas(canvas_frame, bg=COL_PANEL, highlightthickness=0,
                                     yscrollcommand=scrollbar.set)
        self.ram_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.ram_canvas.yview)

        self.ram_list = tk.Frame(self.ram_canvas, bg=COL_PANEL)
        self._ram_list_win = self.ram_canvas.create_window((0, 0), window=self.ram_list, anchor="nw")

        def _on_list_config(e):
            self.ram_canvas.configure(scrollregion=self.ram_canvas.bbox("all"))
        self.ram_list.bind("<Configure>", _on_list_config)

        def _on_canvas_config(e):
            self.ram_canvas.itemconfig(self._ram_list_win, width=e.width)
        self.ram_canvas.bind("<Configure>", _on_canvas_config)

        def _on_mousewheel(e):
            self.ram_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        self.ram_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self._ram_placeholder(
            "Нажмите «ЗАПУСТИТЬ СКАНИРОВАНИЕ» для анализа модулей ОЗУ.\n"
            "Проверяются: производитель, модель, тип, слоты, частота (XMP/DOCP/EXPO), напряжение."
        )

    def _build_summary_placeholder(self):
        for w in self.summary_frame.winfo_children():
            w.destroy()
        inner = tk.Frame(self.summary_frame, bg=COL_PANEL)
        inner.pack(fill="x", padx=14, pady=10)
        tk.Label(inner, text="Сводка появится после сканирования \u2014", font=FONT_SMALL,
                 bg=COL_PANEL, fg=COL_TEXT_DIM).pack(anchor="w")

    def _metric_block(self, parent, label, value, color=COL_WHITE):
        f = tk.Frame(parent, bg=COL_PANEL)
        f.pack(side="left", padx=(0, 26))
        tk.Label(f, text=value, font=("Consolas", 16, "bold"),
                 bg=COL_PANEL, fg=color).pack(anchor="w")
        tk.Label(f, text=label, font=("Consolas", 8),
                 bg=COL_PANEL, fg=COL_TEXT_DIM).pack(anchor="w")

    def _clear_ram_list(self):
        for w in self.ram_list.winfo_children():
            w.destroy()
        self.ram_canvas.yview_moveto(0)

    def _ram_placeholder(self, text):
        self._clear_ram_list()
        tk.Label(self.ram_list, text=text, font=FONT_SMALL, bg=COL_PANEL,
                 fg=COL_TEXT_DIM, justify="left", anchor="w",
                 wraplength=630).pack(fill="x", padx=14, pady=14)

    def _banner(self, text, color, sub=None):
        f = tk.Frame(self.ram_list, bg=COL_PANEL_2, highlightbackground=color,
                     highlightthickness=1)
        f.pack(fill="x", padx=12, pady=(12, 8))
        tk.Label(f, text=text, font=FONT_HEAD, bg=COL_PANEL_2, fg=color,
                 anchor="w", justify="left", wraplength=600).pack(
                     fill="x", padx=12, pady=(8, 2 if sub else 8))
        if sub:
            tk.Label(f, text=sub, font=FONT_SMALL, bg=COL_PANEL_2, fg=COL_TEXT_DIM,
                     anchor="w", justify="left", wraplength=600).pack(
                         fill="x", padx=12, pady=(0, 8))

    def _module_card(self, m, status_tag):
        status_color = {"ok": COL_GREEN, "warn": COL_YELLOW, "dim": COL_TEXT_DIM}[status_tag]
        status_text = {"ok": "НОРМА", "warn": "НИЖЕ ЗАЯВЛЕННОЙ", "dim": "НЕ ОПРЕДЕЛЕНО"}[status_tag]

        card = tk.Frame(self.ram_list, bg=COL_PANEL_2, highlightbackground=COL_BORDER,
                         highlightthickness=1)
        card.pack(fill="x", padx=12, pady=5)

        stripe = tk.Frame(card, bg=status_color, width=4)
        stripe.pack(side="left", fill="y")

        content = tk.Frame(card, bg=COL_PANEL_2)
        content.pack(side="left", fill="both", expand=True, padx=(10, 10), pady=8)

        head = tk.Frame(content, bg=COL_PANEL_2)
        head.pack(fill="x")
        tk.Label(head, text=f'[{m["slot"]}]', font=FONT_MONO_B, bg=COL_PANEL_2,
                 fg=COL_RED).pack(side="left")
        tk.Label(head, text=f'  {m["manufacturer"]}  \u2022  {m["part"]}',
                 font=FONT_MONO_B, bg=COL_PANEL_2, fg=COL_WHITE).pack(side="left")
        tk.Label(head, text=status_text, font=FONT_SMALL, bg=COL_PANEL_2,
                 fg=status_color).pack(side="right")

        grid = tk.Frame(content, bg=COL_PANEL_2)
        grid.pack(fill="x", pady=(6, 0))

        speed_s = f'{m["speed"]} MT/s' if m["speed"] else 'Н/Д'
        cur_s = f'{m["current"]} MT/s' if m["current"] else 'Н/Д'
        volt_s = f'{int(m["voltage"])/1000:.2f} В' if m["voltage"] and int(m["voltage"]) else 'Н/Д'

        fields = [
            ("ТИП", m["type"]),
            ("ОБЪЁМ", f'{m["cap"]} ГБ'),
            ("ЗАЯВЛЕНО", speed_s),
            ("ТЕКУЩАЯ", cur_s),
            ("ФОРМ-ФАКТОР", m["form"]),
            ("НАПРЯЖЕНИЕ", volt_s),
        ]
        for i, (label, value) in enumerate(fields):
            col = tk.Frame(grid, bg=COL_PANEL_2)
            col.grid(row=0, column=i, sticky="w", padx=(0, 18))
            tk.Label(col, text=label, font=("Consolas", 7), bg=COL_PANEL_2,
                     fg=COL_TEXT_DIM).pack(anchor="w")
            val_color = status_color if label in ("ЗАЯВЛЕНО", "ТЕКУЩАЯ") and status_tag != "ok" else COL_TEXT
            tk.Label(col, text=value, font=("Consolas", 9, "bold"), bg=COL_PANEL_2,
                     fg=val_color).pack(anchor="w")

        tk.Label(content, text=f'S/N: {m["serial"]}', font=("Consolas", 7),
                 bg=COL_PANEL_2, fg=COL_TEXT_DIM).pack(anchor="w", pady=(6, 0))

    def _start_ram_scan(self):
        self.scan_btn.config(state="disabled", text="СКАНИРОВАНИЕ...", bg=COL_RED_DARK)
        self.copy_btn.config(state="disabled")
        self.ram_status_lbl.config(text="\u25cf ИДЁТ ПРОВЕРКА", fg=COL_YELLOW)
        self._ram_placeholder("Опрос WMI / CIM \u2026 ожидайте.")
        self._last_report_text = ""
        threading.Thread(target=self._ram_scan_worker, daemon=True).start()

    def _ram_scan_worker(self):
        result = run_ram_check()
        self.after(0, lambda: self._render_ram_result(result))

    def _render_ram_result(self, result):
        self.scan_btn.config(state="normal", text="\u25b6  ЗАПУСТИТЬ СКАНИРОВАНИЕ", bg=COL_RED)
        self._clear_ram_list()

        if "error" in result:
            self.ram_status_lbl.config(text="\u25cf ОШИБКА", fg=COL_RED)
            self._banner("ОШИБКА СКАНИРОВАНИЯ", COL_RED, result["error"])
            self._build_summary_placeholder()
            return

        summary = result["summary"]
        modules = result["modules"]

        for w in self.summary_frame.winfo_children():
            w.destroy()
        inner = tk.Frame(self.summary_frame, bg=COL_PANEL)
        inner.pack(fill="x", padx=14, pady=10)

        load_pct = int(summary["load_pct"])
        load_color = COL_GREEN if load_pct < 60 else (COL_YELLOW if load_pct < 85 else COL_RED)

        self._metric_block(inner, "ВСЕГО ОЗУ (ГБ)", summary["total_gb"], COL_WHITE)
        self._metric_block(inner, "МОДУЛЕЙ", summary["count"], COL_WHITE)
        self._metric_block(inner, "СЛОТЫ", f'{summary["slots_used"]}/{summary["slots_max"]}', COL_TEXT)
        self._metric_block(inner, "ИСПОЛЬЗОВАНО (ГБ)", summary["used_gb"], COL_TEXT)
        self._metric_block(inner, "СВОБОДНО (ГБ)", summary["free_gb"], COL_TEXT)
        self._metric_block(inner, "ЗАГРУЗКА", f'{load_pct}%', load_color)

        # Визуальная полоса загрузки ОЗУ
        bar_wrap = tk.Frame(self.summary_frame, bg=COL_PANEL)
        bar_wrap.pack(fill="x", padx=14, pady=(0, 12))
        bar_track = tk.Canvas(bar_wrap, height=6, bg=COL_PANEL_2, highlightthickness=0)
        bar_track.pack(fill="x")

        def _draw_bar(event=None, pct=load_pct, color=load_color, canvas=bar_track):
            canvas.delete("all")
            w = canvas.winfo_width() or 1
            canvas.create_rectangle(0, 0, w, 6, fill=COL_PANEL_2, outline="")
            fill_w = max(2, int(w * pct / 100))
            canvas.create_rectangle(0, 0, fill_w, 6, fill=color, outline="")

        bar_track.bind("<Configure>", _draw_bar)

        slow_count = 0
        unknown_count = 0
        classified = []
        for m in modules:
            speed, cur = m["speed"], m["current"]
            if cur > 0 and speed > 0 and cur < speed:
                tag = "warn"
                slow_count += 1
            elif cur == 0 or speed == 0:
                tag = "dim"
                unknown_count += 1
            else:
                tag = "ok"
            classified.append((m, tag))

        if slow_count == 0 and unknown_count == 0:
            self.ram_status_lbl.config(text="\u25cf ВСЁ В НОРМЕ", fg=COL_GREEN)
            self._banner("\u2713  ВСЕ МОДУЛИ РАБОТАЮТ НА ЗАЯВЛЕННОЙ ЧАСТОТЕ", COL_GREEN)
        elif slow_count > 0:
            self.ram_status_lbl.config(text="\u25cf ВНИМАНИЕ", fg=COL_YELLOW)
            slow_word = ru_plural(slow_count, "МОДУЛЬ", "МОДУЛЯ", "МОДУЛЕЙ").upper()
            self._banner(
                f"\u26a0  {slow_count} {slow_word} НИЖЕ ЗАЯВЛЕННОЙ ЧАСТОТЫ",
                COL_YELLOW, "Проверьте XMP / DOCP / EXPO в настройках BIOS."
            )
        else:
            self.ram_status_lbl.config(text="\u25cf ЧАСТИЧНО", fg=COL_TEXT_DIM)
            self._banner("ЧАСТОТА ОПРЕДЕЛЕНА НЕ ДЛЯ ВСЕХ МОДУЛЕЙ", COL_TEXT_DIM)

        types_seen = set(m["type"] for m in modules)
        if len(types_seen) > 1:
            self._banner("\u2716  ОБНАРУЖЕНЫ РАЗНЫЕ ТИПЫ ПАМЯТИ В СИСТЕМЕ", COL_RED)

        if unknown_count > 0:
            tk.Label(self.ram_list,
                     text=f"Примечание: для {unknown_count} "
                          f"{ru_plural(unknown_count, 'модуля', 'модулей', 'модулей')} "
                          f"частота не определена (данные недоступны).",
                     font=FONT_SMALL, bg=COL_PANEL, fg=COL_TEXT_DIM, anchor="w",
                     wraplength=630, justify="left").pack(fill="x", padx=16, pady=(0, 4))

        for m, tag in classified:
            self._module_card(m, tag)

        tk.Frame(self.ram_list, bg=COL_PANEL, height=8).pack()

        report_lines = [
            f'NOA RUST TOOL \u2014 ОТЧЁТ RAM CHECK',
            f'Всего ОЗУ: {summary["total_gb"]} ГБ | Модулей: {summary["count"]} | '
            f'Слоты: {summary["slots_used"]}/{summary["slots_max"]} | Загрузка: {load_pct}%',
            '-' * 56,
        ]
        for m, tag in classified:
            status = {"ok": "НОРМА", "warn": "НИЖЕ ЗАЯВЛЕННОЙ", "dim": "Н/Д"}[tag]
            speed_s = f'{m["speed"]} MT/s' if m["speed"] else 'Н/Д'
            cur_s = f'{m["current"]} MT/s' if m["current"] else 'Н/Д'
            report_lines.append(
                f'[{m["slot"]}] {m["manufacturer"]} {m["part"]} | {m["type"]} {m["cap"]}ГБ | '
                f'{speed_s} -> {cur_s} | {status}'
            )
        if slow_count == 0 and unknown_count == 0:
            report_lines.append('СТАТУС: Все модули работают на заявленной частоте.')
        elif slow_count > 0:
            w = ru_plural(slow_count, 'модуль', 'модуля', 'модулей')
            report_lines.append(f'ВНИМАНИЕ: {slow_count} {w} ниже заявленной частоты. Проверьте XMP/DOCP/EXPO.')
        if unknown_count > 0:
            w2 = ru_plural(unknown_count, 'модуля', 'модулей', 'модулей')
            report_lines.append(f'Примечание: для {unknown_count} {w2} частота не определена.')

        self._last_report_text = "\n".join(report_lines)
        self.copy_btn.config(state="normal")

    def _copy_report(self):
        if getattr(self, "_last_report_text", ""):
            self.clipboard_clear()
            self.clipboard_append(self._last_report_text)
            self.copy_btn.config(text="СКОПИРОВАНО \u2713")
            self.after(1500, lambda: self.copy_btn.config(text="КОПИРОВАТЬ ОТЧЁТ"))

    # ===========================================================
    #   ВКЛАДКА: OPTIMIZATION
    # ===========================================================
    def _build_opt_tab(self, parent):
        top = tk.Frame(parent, bg=COL_BG)
        top.pack(side="top", fill="x", padx=16, pady=(12, 8))

        tk.Label(top, text="ОПТИМИЗАЦИЯ СИСТЕМЫ",
                 font=FONT_HEAD, bg=COL_BG, fg=COL_WHITE).pack(side="left")

        restore_btn = tk.Button(
            top, text="СОЗДАТЬ ТОЧКУ ВОССТАНОВЛЕНИЯ", font=FONT_MONO_B,
            bg=COL_RED_DARK, fg=COL_WHITE, activebackground=COL_RED,
            activeforeground=COL_WHITE, relief="flat", bd=0, padx=12, pady=6,
            cursor="hand2", command=self._open_restore_point
        )
        restore_btn.pack(side="right")
        add_hover(restore_btn, COL_RED_DARK, COL_RED)

        refresh_btn = tk.Button(
            top, text="\u21bb  ОБНОВИТЬ СТАТУСЫ", font=FONT_MONO,
            bg=COL_PANEL_2, fg=COL_TEXT, activebackground=COL_PANEL,
            relief="flat", bd=0, padx=10, pady=6, cursor="hand2",
            command=self._refresh_all_opt_status
        )
        refresh_btn.pack(side="right", padx=(0, 8))
        add_hover(refresh_btn, COL_PANEL_2, COL_BORDER)

        warn = tk.Frame(parent, bg=COL_PANEL, highlightbackground=COL_YELLOW, highlightthickness=1)
        warn.pack(side="top", fill="x", padx=16, pady=(0, 10))
        tk.Label(warn, text="⚠  Рекомендуется создать точку восстановления перед применением твиков. "
                            "Некоторые изменения требуют прав администратора.",
                 font=FONT_SMALL, bg=COL_PANEL, fg=COL_YELLOW, padx=12, pady=6,
                 wraplength=1100, justify="left").pack(anchor="w")

        outer = tk.Frame(parent, bg=COL_BG)
        outer.pack(side="top", fill="both", expand=True, padx=16, pady=(0, 14))

        canvas = tk.Canvas(outer, bg=COL_BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview,
                                  bg=COL_PANEL, troughcolor=COL_BG, activebackground=COL_RED_DARK)
        self.opt_list = tk.Frame(canvas, bg=COL_BG)

        self.opt_list.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.opt_list, anchor="nw", tags="optframe")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_canvas_cfg(e):
            canvas.itemconfig("optframe", width=e.width)
        canvas.bind("<Configure>", _on_canvas_cfg)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _mw(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _mw)

        # Блоки функций
        blocks = [
            {
                "title": "⚡  ПИТАНИЕ",
                "features": [
                    {
                        "key": "high_perf",
                        "title": "Enable High Performance Power Plan",
                        "desc": "Переключает план питания Windows на «Высокая производительность».",
                    },
                    {
                        "key": "ultimate_perf",
                        "title": "Enable Ultimate Performance Power Plan",
                        "desc": "Создаёт и включает режим «Максимальная производительность».\n"
                                "Команда: powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61\n"
                                "При отключении возвращает предыдущий план питания.",
                    },
                ],
            },
            {
                "title": "🎮  ИГРОВАЯ ОПТИМИЗАЦИЯ",
                "features": [
                    {
                        "key": "game_mode",
                        "title": "Enable Windows Game Mode",
                        "desc": "Включает игровой режим Windows.\nПараметры → Игры → Игровой режим → Вкл.\nПри отключении возвращает стандартное состояние.",
                    },
                    {
                        "key": "game_optimize",
                        "title": "Enable Game System Profile (MMCSS)",
                        "desc": "Твик реестра HKLM\\...\\Multimedia\\SystemProfile\\Tasks\\Games:\n"
                                "GPU Priority=8, Priority=6, Scheduling Category=High, SFIO Priority=High.\n"
                                "Требует права администратора.",
                    },
                    {
                        "key": "xbox_gamebar",
                        "title": "Disable Xbox Game Bar",
                        "desc": "Отключает Xbox Game Bar.\nПараметры → Игры → Xbox Game Bar.",
                    },
                    {
                        "key": "bg_recording",
                        "title": "Disable Background Recording",
                        "desc": "Отключает запись в фоне.\nПараметры → Игры → Захваты.",
                    },
                    {
                        "key": "rust_priority",
                        "title": "Set Rust Process Priority = High",
                        "desc": "Повышает приоритет процесса RustClient.exe / Rust.exe до High.\n"
                                "Игра должна быть уже запущена. Действует до перезапуска игры.",
                    },
                ],
            },
            {
                "title": "🧹  СИСТЕМА И ОТВЛЕЧЕНИЯ",
                "features": [
                    {
                        "key": "startup",
                        "title": "Disable Known Startup Apps",
                        "desc": "Отключает известные автозагружаемые приложения (Discord, Steam, "
                                "лаунчеры, RGB-софт и т.п.) из реестра Run.\n"
                                "Запрашивает подтверждение перед изменением. Приложения не удаляются.",
                    },
                    {
                        "key": "mouse_accel",
                        "title": "Disable Mouse Acceleration",
                        "desc": "Отключает ускорение указателя мыши (Enhance Pointer Precision) —\n"
                                "делает движение мыши линейным и предсказуемым для прицеливания.",
                    },
                    {
                        "key": "notifications",
                        "title": "Disable Windows Notifications",
                        "desc": "Отключает всплывающие тосты Windows на время игровой сессии,\n"
                                "чтобы уведомления не отвлекали и не перекрывали экран.",
                    },
                ],
            },
        ]

        for block in blocks:
            self._create_opt_block_header(self.opt_list, block["title"])
            for feat in block["features"]:
                self._create_opt_card(self.opt_list, feat)

        # Быстрые ссылки
        quick = tk.Frame(self.opt_list, bg=COL_PANEL, highlightbackground=COL_BORDER, highlightthickness=1)
        quick.pack(fill="x", pady=(12, 8), padx=4)

        tk.Label(quick, text="БЫСТРЫЕ ССЫЛКИ НА НАСТРОЙКИ WINDOWS",
                 font=FONT_SMALL, bg=COL_PANEL, fg=COL_RED).pack(anchor="w", padx=12, pady=(8, 4))

        btn_row = tk.Frame(quick, bg=COL_PANEL)
        btn_row.pack(fill="x", padx=12, pady=(0, 10))

        quick_actions = [
            ("Game Mode", "ms-settings:gaming-gamemode"),
            ("Xbox Game Bar", "ms-settings:gaming-gamebar"),
            ("Captures / Захваты", "ms-settings:gaming-gamedvr"),
            ("Power Options", "powercfg.cpl"),
        ]

        for text, target in quick_actions:
            b = tk.Button(
                btn_row, text=text, font=("Consolas", 8),
                bg=COL_PANEL_2, fg=COL_TEXT, relief="flat", bd=0, padx=8, pady=4,
                cursor="hand2",
                command=lambda t=target: self._open_settings(t)
            )
            b.pack(side="left", padx=(0, 6))
            add_hover(b, COL_PANEL_2, COL_RED_DARK, COL_TEXT, COL_WHITE)

        tk.Frame(self.opt_list, bg=COL_BG, height=20).pack()



    def _create_opt_block_header(self, parent, title):
        hdr = tk.Frame(parent, bg=COL_BG)
        hdr.pack(fill="x", pady=(14, 4), padx=4)

        tk.Label(
            hdr, text=title, font=("Consolas", 11, "bold"),
            bg=COL_BG, fg=COL_RED
        ).pack(side="left")

        # Линия справа от заголовка
        line = tk.Frame(hdr, bg=COL_BORDER, height=1)
        line.pack(side="left", fill="x", expand=True, padx=(12, 0), pady=6)

    def _create_opt_card(self, parent, feat):
        key = feat["key"]
        card = tk.Frame(parent, bg=COL_PANEL_2, highlightbackground=COL_BORDER, highlightthickness=1)
        card.pack(fill="x", pady=5, padx=4)


        stripe = tk.Frame(card, bg=COL_RED_DIM, width=4)
        stripe.pack(side="left", fill="y")
        self.opt_cards[key] = {"stripe": stripe, "card": card}

        content = tk.Frame(card, bg=COL_PANEL_2)
        content.pack(side="left", fill="both", expand=True, padx=12, pady=10)

        # Заголовок: название + статус + переключатель
        head = tk.Frame(content, bg=COL_PANEL_2)
        head.pack(fill="x")

        tk.Label(head, text=feat["title"], font=FONT_MONO_B,
                 bg=COL_PANEL_2, fg=COL_WHITE).pack(side="left")

        status_lbl = tk.Label(head, text="● ПРОВЕРКА...", font=FONT_SMALL,
                              bg=COL_PANEL_2, fg=COL_TEXT_DIM)
        status_lbl.pack(side="left", padx=(12, 0))
        self.opt_status_lbls[key] = status_lbl

        # Переключатель справа
        toggle = ToggleSwitch(
            head,
            command=lambda state, k=key: self._on_toggle(k, state)
        )
        toggle.pack(side="right")
        self.opt_vars[key] = toggle  # теперь храним сам виджет

        # Описание
        tk.Label(content, text=feat["desc"], font=FONT_SMALL, bg=COL_PANEL_2,
                 fg=COL_TEXT_DIM, justify="left", anchor="w",
                 wraplength=900).pack(fill="x", pady=(6, 8))

        # Кнопки: только ОТКАТ и ОТКРЫТЬ НАСТРОЙКИ (применение автоматическое)
        btn_row = tk.Frame(content, bg=COL_PANEL_2)
        btn_row.pack(fill="x")

        roll_btn = tk.Button(
            btn_row, text="\u21b6 ОТКАТ", font=FONT_MONO,
            bg=COL_PANEL, fg=COL_TEXT_DIM, activebackground=COL_BORDER,
            relief="flat", bd=0, padx=12, pady=5, cursor="hand2",
            command=lambda k=key: self._on_rollback(k)
        )
        roll_btn.pack(side="left")
        add_hover(roll_btn, COL_PANEL, COL_BORDER, COL_TEXT_DIM, COL_WHITE)

        open_btn = tk.Button(
            btn_row, text="\u2699 ОТКРЫТЬ НАСТРОЙКИ", font=FONT_MONO,
            bg=COL_PANEL, fg=COL_TEXT_DIM, activebackground=COL_BORDER,
            relief="flat", bd=0, padx=10, pady=5, cursor="hand2",
            command=lambda k=key: self._open_feature_settings(k)
        )
        open_btn.pack(side="left", padx=(8, 0))
        add_hover(open_btn, COL_PANEL, COL_BORDER, COL_TEXT_DIM, COL_WHITE)

        # Лёгкая подсветка рамки карточки при наведении — усиливает ощущение интерактивности
        def _card_enter(e):
            card.config(highlightbackground=COL_RED_DIM)

        def _card_leave(e):
            card.config(highlightbackground=COL_BORDER)

        for w in (card, content, head):
            w.bind("<Enter>", _card_enter)
            w.bind("<Leave>", _card_leave)


    def _set_status(self, key, text, color):
        lbl = self.opt_status_lbls.get(key)
        if lbl:
            lbl.config(text=text, fg=color)
        stripe = self.opt_cards.get(key, {}).get("stripe")
        if stripe:
            stripe.config(bg=color if color != COL_TEXT_DIM else COL_RED_DIM)

    def _refresh_all_opt_status(self):
        mapping = {
            "game_mode": self._get_game_mode,
            "high_perf": self._get_high_perf,
            "ultimate_perf": self._get_ultimate_perf,
            "game_optimize": self._get_game_optimize,
            "xbox_gamebar": self._get_xbox_gamebar,
            "bg_recording": self._get_bg_recording,
            "rust_priority": self._get_rust_priority,
            "mouse_accel": self._get_mouse_accel,
            "notifications": self._get_notifications,
            "startup": self._get_startup_status,
        }

        for key, getter in mapping.items():
            if key not in self.opt_status_lbls:
                continue
            toggle = self.opt_vars.get(key)
            try:
                state = getter()
                if key == "startup":
                    # Семантика особая: True = найдено что чистить, False = чисто.
                    # Тумблер тут не отражает "вкл/выкл", просто держим его выключенным.
                    if toggle:
                        toggle.set(False)
                    if state is True:
                        self._set_status(key, "● НАЙДЕНЫ ЗАПИСИ", COL_YELLOW)
                    elif state is False:
                        self._set_status(key, "● ЧИСТО", COL_GREEN)
                    else:
                        self._set_status(key, "● НЕИЗВЕСТНО", COL_YELLOW)
                elif state is True:
                    self._set_status(key, "● АКТИВНО", COL_GREEN)
                    if toggle:
                        toggle.set(True)  # без trigger
                elif state is False:
                    self._set_status(key, "● ВЫКЛЮЧЕНО", COL_TEXT_DIM)
                    if toggle:
                        toggle.set(False)
                else:
                    self._set_status(key, "● НЕИЗВЕСТНО", COL_YELLOW)
            except Exception:
                self._set_status(key, "● ОШИБКА ЧТЕНИЯ", COL_RED)

    def _on_toggle(self, key, desired):
        """Автоприменение при переключении тумблера."""
        toggle = self.opt_vars.get(key)
        if toggle:
            toggle._busy = True
        try:
            # Сохраняем предыдущее состояние для отката.
            # mouse_accel и game_optimize сами управляют своим бэкапом
            # (под ключами "mouse" / "game_optimize" с более богатой структурой),
            # поэтому не перезаписываем их плоским булевым значением.
            SELF_MANAGED_BACKUP = {"mouse_accel", "game_optimize"}
            getter = getattr(self, f"_get_{key}", None)
            if getter and key not in self.opt_backup and key not in SELF_MANAGED_BACKUP:
                current = getter()
                if current is not None:
                    self.opt_backup[key] = current

            apply_fn = getattr(self, f"_apply_{key}", None)
            if not apply_fn:
                self._set_status(key, "● НЕТ ФУНКЦИИ", COL_RED)
                return

            ok, msg = apply_fn(desired)
            if ok:
                self._set_status(key, "● ПРИМЕНЕНО", COL_GREEN if desired else COL_TEXT_DIM)
            elif msg == "Отменено пользователем.":
                # Пользователь сам отменил подтверждающий диалог — это не ошибка
                if toggle:
                    toggle.set(not desired)
                self._set_status(key, "● ОТМЕНЕНО", COL_TEXT_DIM)
            else:
                # Откатываем визуально тумблер назад
                if toggle:
                    toggle.set(not desired)
                self._set_status(key, "● ОШИБКА", COL_RED)
                messagebox.showerror("NOA RUST TOOL", f"Не удалось применить:\n{msg}")
        except Exception as e:
            if toggle:
                toggle.set(not desired)
            messagebox.showerror("NOA", str(e))
        finally:
            if toggle:
                toggle._busy = False
            self.after(600, self._refresh_all_opt_status)


    def _on_rollback(self, key):
        try:
            roll_fn = getattr(self, f"_rollback_{key}", None)
            if not roll_fn:
                # fallback for power plans
                if key in ("high_perf", "ultimate_perf"):
                    ok, msg = self._rollback_power_plan()
                else:
                    messagebox.showwarning("NOA", "Откат для этой функции не реализован.")
                    return
            else:
                ok, msg = roll_fn()
            if ok:
                self._set_status(key, "● ОТКАЧЕНО", COL_YELLOW)
                messagebox.showinfo("NOA RUST TOOL", f"Откат выполнен.\n{msg}")
            else:
                messagebox.showwarning("NOA", f"Откат:\n{msg}")
            self.after(500, self._refresh_all_opt_status)
        except Exception as e:
            messagebox.showerror("NOA", str(e))

    def _open_restore_point(self):
        try:
            subprocess.Popen(
                ["rundll32.exe", "shell32.dll,Control_RunDLL", "sysdm.cpl,,4"],
                shell=False
            )
        except Exception as e:
            messagebox.showerror("NOA", f"Не удалось открыть:\n{e}")

    def _open_settings(self, target):
        try:
            if target.endswith(".cpl"):
                subprocess.Popen(["control", target], shell=False)
            else:
                os.startfile(target)
        except Exception:
            try:
                subprocess.Popen(f'start "" "{target}"', shell=True)
            except Exception as e:
                messagebox.showerror("NOA", str(e))

    def _open_feature_settings(self, key):
        mapping = {
            "game_mode": "ms-settings:gaming-gamemode",
            "high_perf": "powercfg.cpl",
            "ultimate_perf": "powercfg.cpl",
            "game_optimize": None,
            "xbox_gamebar": "ms-settings:gaming-gamebar",
            "bg_recording": "ms-settings:gaming-gamedvr",
            "mouse_accel": "main.cpl",
            "notifications": "ms-settings:notifications",
            "startup": "ms-settings:startupapps",
            "rust_priority": None,
        }
        t = mapping.get(key)
        if t:
            self._open_settings(t)
        elif key == "game_optimize":
            messagebox.showinfo(
                "NOA",
                "Это твик реестра:\n"
                "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\"
                "Multimedia\\SystemProfile\\Tasks\\Games\n\n"
                "Отдельной страницы настроек нет."
            )
        elif key == "rust_priority":
            messagebox.showinfo(
                "NOA",
                "Отдельной страницы настроек нет.\n"
                "Запустите RustClient.exe / Rust.exe, затем нажмите переключатель ещё раз."
            )



    # ===========================================================
    #   РЕАЛИЗАЦИЯ ФУНКЦИЙ
    # ===========================================================

    # ----- Game Mode -----
    def _get_game_mode(self):
        if not winreg:
            return None
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\GameBar", 0, winreg.KEY_READ) as k:
                val, _ = winreg.QueryValueEx(k, "AutoGameModeEnabled")
                return bool(val)
        except FileNotFoundError:
            return False
        except Exception:
            return None

    def _apply_game_mode(self, enable):
        if not winreg:
            return False, "winreg недоступен"
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\GameBar")
            winreg.SetValueEx(key, "AutoGameModeEnabled", 0, winreg.REG_DWORD, 1 if enable else 0)
            winreg.SetValueEx(key, "AllowAutoGameMode", 0, winreg.REG_DWORD, 1 if enable else 0)
            winreg.CloseKey(key)
            return True, f"Game Mode {'включён' if enable else 'выключен'}."
        except Exception as e:
            return False, str(e)

    def _rollback_game_mode(self):
        prev = self.opt_backup.get("game_mode")
        if prev is None:
            return False, "Нет сохранённого состояния для отката."
        return self._apply_game_mode(bool(prev))

    # ----- Power Plans -----
    HIGH_PERF_GUID = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
    BALANCED_GUID = "381b4222-f694-41f0-9685-ff5bb260df2e"
    ULTIMATE_BASE = "e9a42b02-d5df-448d-aa00-03f14749eb61"

    def _get_active_power_guid(self):
        ok, out, _ = _run_cmd(["powercfg", "/getactivescheme"])
        if not ok:
            return None
        m = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", out)
        return m.group(1).lower() if m else None

    def _get_high_perf(self):
        guid = self._get_active_power_guid()
        if guid is None:
            return None
        return guid == self.HIGH_PERF_GUID.lower()

    def _apply_high_perf(self, enable):
        current = self._get_active_power_guid()
        if "power_plan" not in self.opt_backup and current:
            self.opt_backup["power_plan"] = current

        if enable:
            ok, out, err = _run_cmd(["powercfg", "/setactive", self.HIGH_PERF_GUID])
            return (ok, "План «Высокая производительность» активирован." if ok else (err or out))
        else:
            target = self.opt_backup.get("power_plan") or self.BALANCED_GUID
            ok, _, err = _run_cmd(["powercfg", "/setactive", target])
            return (ok, "План питания возвращён." if ok else err)

    def _find_ultimate_guid(self):
        """Ищет уже созданный Ultimate Performance в списке схем."""
        # 1) Сохранённый нами GUID
        stored = (self.opt_backup.get("ultimate_guid") or "").lower()
        if stored:
            return stored

        # 2) Ищем по имени в powercfg /list
        ok, out, _ = _run_cmd(["powercfg", "/list"])
        if not ok:
            return None
        for line in out.splitlines():
            low = line.lower()
            if ("ultimate" in low or "максимальн" in low or "maximum performance" in low):
                m = re.search(
                    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})",
                    line
                )
                if m:
                    guid = m.group(1).lower()
                    self.opt_backup["ultimate_guid"] = guid
                    return guid
        return None

    def _get_ultimate_perf(self):
        active = self._get_active_power_guid()
        if not active:
            return None

        # Базовый GUID Ultimate (если вдруг активирован напрямую)
        if active == self.ULTIMATE_BASE.lower():
            return True

        ult = self._find_ultimate_guid()
        if ult and active == ult:
            return True

        # Доп. проверка по имени активной схемы
        ok, out, _ = _run_cmd(["powercfg", "/getactivescheme"])
        if ok:
            low = out.lower()
            if "ultimate" in low or "максимальн" in low or "maximum performance" in low:
                return True

        return False

    def _apply_ultimate_perf(self, enable):
        current = self._get_active_power_guid()
        if "power_plan" not in self.opt_backup and current:
            # Не сохраняем сам ultimate как "предыдущий"
            ult = self._find_ultimate_guid()
            if not ult or current != ult:
                self.opt_backup["power_plan"] = current

        if enable:
            # Сначала пробуем найти уже существующий Ultimate
            guid = self._find_ultimate_guid()
            if not guid:
                ok, out, err = _run_cmd(["powercfg", "-duplicatescheme", self.ULTIMATE_BASE])
                if not ok:
                    return False, err or out or "Не удалось создать Ultimate Performance (нужны права админа)"
                m = re.search(
                    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})",
                    out
                )
                if not m:
                    return False, "Не удалось получить GUID новой схемы."
                guid = m.group(1).lower()
                self.opt_backup["ultimate_guid"] = guid

            ok2, _, err2 = _run_cmd(["powercfg", "/setactive", guid])
            if ok2:
                self.opt_backup["ultimate_guid"] = guid
                return True, f"Ultimate Performance активирован."
            return False, err2 or "Не удалось активировать план"
        else:
            return self._rollback_power_plan()

    def _rollback_power_plan(self):
        prev = self.opt_backup.get("power_plan") or self.BALANCED_GUID
        # Не откатываем на ultimate
        ult = (self.opt_backup.get("ultimate_guid") or "").lower()
        if prev and prev.lower() == ult:
            prev = self.BALANCED_GUID
        ok, _, err = _run_cmd(["powercfg", "/setactive", prev])
        return (ok, f"Восстановлен план: {prev}" if ok else err)

    def _rollback_high_perf(self):
        return self._rollback_power_plan()

    def _rollback_ultimate_perf(self):
        return self._rollback_power_plan()


    # ----- Game System Profile (MMCSS) -----
    GAMES_PROFILE_PATH = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games"
    GAMES_PROFILE_VALUES = {
        "GPU Priority": (winreg.REG_DWORD if winreg else 4, 8),
        "Priority": (winreg.REG_DWORD if winreg else 4, 6),
        "Scheduling Category": (winreg.REG_SZ if winreg else 1, "High"),
        "SFIO Priority": (winreg.REG_SZ if winreg else 1, "High"),
    }

    def _get_game_optimize(self):
        if not winreg:
            return None
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, self.GAMES_PROFILE_PATH, 0, winreg.KEY_READ) as k:
                for name, (typ, expected) in self.GAMES_PROFILE_VALUES.items():
                    try:
                        val, _ = winreg.QueryValueEx(k, name)
                        if typ == winreg.REG_DWORD:
                            if int(val) != int(expected):
                                return False
                        else:
                            if str(val) != str(expected):
                                return False
                    except FileNotFoundError:
                        return False
                return True
        except FileNotFoundError:
            return False
        except PermissionError:
            return None
        except Exception:
            return None

    def _apply_game_optimize(self, enable):
        if not winreg:
            return False, "winreg недоступен"
        try:
            # Сохраняем старые значения
            if "game_optimize" not in self.opt_backup:
                old = {}
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, self.GAMES_PROFILE_PATH, 0, winreg.KEY_READ) as k:
                        for name in self.GAMES_PROFILE_VALUES:
                            try:
                                val, typ = winreg.QueryValueEx(k, name)
                                old[name] = (val, typ)
                            except FileNotFoundError:
                                old[name] = None
                except Exception:
                    old = {}
                self.opt_backup["game_optimize"] = old

            key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, self.GAMES_PROFILE_PATH)
            if enable:
                for name, (typ, val) in self.GAMES_PROFILE_VALUES.items():
                    winreg.SetValueEx(key, name, 0, typ, val)
            else:
                # Откат к сохранённым или разумным дефолтам Windows
                defaults = {
                    "GPU Priority": (winreg.REG_DWORD, 2),
                    "Priority": (winreg.REG_DWORD, 2),
                    "Scheduling Category": (winreg.REG_SZ, "Medium"),
                    "SFIO Priority": (winreg.REG_SZ, "Normal"),
                }
                prev = self.opt_backup.get("game_optimize", {})
                for name, (typ, def_val) in defaults.items():
                    if name in prev and prev[name] is not None:
                        old_val, old_typ = prev[name]
                        winreg.SetValueEx(key, name, 0, old_typ, old_val)
                    else:
                        winreg.SetValueEx(key, name, 0, typ, def_val)
            winreg.CloseKey(key)
            return True, (
                "Игровой профиль MMCSS применён (GPU Priority=8, Priority=6, High)."
                if enable else
                "Игровой профиль MMCSS возвращён к предыдущим/стандартным значениям."
            )
        except PermissionError:
            return False, "Нужны права администратора (HKLM)."
        except Exception as e:
            return False, str(e)

    def _rollback_game_optimize(self):
        prev = self.opt_backup.get("game_optimize")
        if prev is None:
            return self._apply_game_optimize(False)
        if not winreg:
            return False, "winreg недоступен"
        try:
            key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, self.GAMES_PROFILE_PATH)
            for name, data in prev.items():
                if data is None:
                    try:
                        winreg.DeleteValue(key, name)
                    except Exception:
                        pass
                else:
                    val, typ = data
                    winreg.SetValueEx(key, name, 0, typ, val)
            winreg.CloseKey(key)
            return True, "Игровой профиль MMCSS восстановлен."
        except PermissionError:
            return False, "Нужны права администратора (HKLM)."
        except Exception as e:
            return False, str(e)

    # ----- Xbox Game Bar -----
    def _get_xbox_gamebar(self):
        if not winreg:
            return None
        try:

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\GameDVR", 0, winreg.KEY_READ) as k:
                val, _ = winreg.QueryValueEx(k, "AppCaptureEnabled")
                return val == 0
        except Exception:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                    r"System\GameConfigStore", 0, winreg.KEY_READ) as k:
                    val, _ = winreg.QueryValueEx(k, "GameDVR_Enabled")
                    return val == 0
            except Exception:
                return None

    def _apply_xbox_gamebar(self, disable):
        if not winreg:
            return False, "winreg недоступен"
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                   r"Software\Microsoft\Windows\CurrentVersion\GameDVR")
            winreg.SetValueEx(key, "AppCaptureEnabled", 0, winreg.REG_DWORD, 0 if disable else 1)
            winreg.CloseKey(key)

            key2 = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"System\GameConfigStore")
            winreg.SetValueEx(key2, "GameDVR_Enabled", 0, winreg.REG_DWORD, 0 if disable else 1)
            winreg.CloseKey(key2)

            try:
                key3 = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\GameBar")
                winreg.SetValueEx(key3, "UseNexusForGameBarEnabled", 0, winreg.REG_DWORD, 0 if disable else 1)
                winreg.CloseKey(key3)
            except Exception:
                pass

            return True, f"Xbox Game Bar {'отключён' if disable else 'включён'}."
        except Exception as e:
            return False, str(e)

    def _rollback_xbox_gamebar(self):
        prev = self.opt_backup.get("xbox_gamebar")
        if prev is None:
            return False, "Нет сохранённого состояния."
        return self._apply_xbox_gamebar(bool(prev))

    # ----- Background Recording -----
    def _get_bg_recording(self):
        if not winreg:
            return None
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\GameDVR", 0, winreg.KEY_READ) as k:
                val, _ = winreg.QueryValueEx(k, "HistoricalCaptureEnabled")
                return val == 0
        except Exception:
            return None

    def _apply_bg_recording(self, disable):
        if not winreg:
            return False, "winreg недоступен"
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                   r"Software\Microsoft\Windows\CurrentVersion\GameDVR")
            winreg.SetValueEx(key, "HistoricalCaptureEnabled", 0, winreg.REG_DWORD, 0 if disable else 1)
            winreg.SetValueEx(key, "HistoricalCaptureOnBatteryEnabled", 0, winreg.REG_DWORD, 0 if disable else 1)
            winreg.CloseKey(key)
            return True, f"Фоновая запись {'отключена' if disable else 'включена'}."
        except Exception as e:
            return False, str(e)

    def _rollback_bg_recording(self):
        prev = self.opt_backup.get("bg_recording")
        if prev is None:
            return False, "Нет сохранённого состояния."
        return self._apply_bg_recording(bool(prev))

    # ----- Startup -----
    STARTUP_TARGETS = [
        "Discord", "Steam", "EpicGamesLauncher", "Battle.net", "Origin",
        "Ubisoft", "GalaxyClient", "iCUE", "ArmouryCrate", "Razer",
        "Logitech", "Corsair", "NZXT", "SignalRgb", "WallpaperEngine",
        "Adobe", "CCXProcess", "OneDrive", "Teams", "Skype"
    ]
    STARTUP_RUN_KEYS = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") if winreg else (None, None),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run") if winreg else (None, None),
    ]

    def _find_startup_matches(self):
        """Возвращает список (root, path, name) для всех записей автозагрузки,
        совпадающих с STARTUP_TARGETS — не удаляя ничего."""
        found = []
        if not winreg:
            return found
        for root, path in self.STARTUP_RUN_KEYS:
            if root is None:
                continue
            try:
                with winreg.OpenKey(root, path, 0, winreg.KEY_READ) as k:
                    i = 0
                    while True:
                        try:
                            name, val, _ = winreg.EnumValue(k, i)
                            for t in self.STARTUP_TARGETS:
                                if t.lower() in name.lower() or t.lower() in str(val).lower():
                                    found.append((root, path, name))
                                    break
                            i += 1
                        except OSError:
                            break
            except Exception:
                pass
        return found

    def _get_startup_status(self):
        """True = найдены известные автозагружаемые приложения (можно почистить),
        False = ничего подходящего не найдено."""
        matches = self._find_startup_matches()
        return len(matches) > 0 if winreg else None

    def _apply_startup(self, enable):
        """enable=True: удалить найденные записи автозагрузки (после подтверждения).
        enable=False: просто открыть настройки автозагрузки Windows."""
        if not enable:
            self._open_settings("ms-settings:startupapps")
            return True, "Открыты настройки автозагрузки."

        matches = self._find_startup_matches()
        if not matches:
            return False, "Известные автозагружаемые приложения не найдены."

        names_preview = ", ".join(sorted(set(n for _, _, n in matches)))
        confirmed = messagebox.askyesno(
            "NOA RUST TOOL — Подтверждение",
            f"Будут отключены следующие записи автозагрузки:\n\n{names_preview}\n\n"
            "Приложения не удаляются, только убираются из автозапуска.\n"
            "Изменения можно откатить кнопкой ОТКАТ.\n\nПродолжить?"
        )
        if not confirmed:
            return False, "Отменено пользователем."

        disabled = []
        if winreg:
            # Группируем найденные совпадения по (root, path), чтобы открывать ключ один раз
            by_key = {}
            for root, path, name in matches:
                by_key.setdefault((root, path), []).append(name)

            for (root, path), names in by_key.items():
                try:
                    with winreg.OpenKey(root, path, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as k:
                        for name in names:
                            try:
                                val, typ = winreg.QueryValueEx(k, name)
                                self.opt_backup.setdefault("startup_deleted", []).append(
                                    (root, path, name, val, typ)
                                )
                                winreg.DeleteValue(k, name)
                                disabled.append(name)
                            except Exception:
                                pass
                except Exception:
                    pass

        if disabled:
            return True, f"Отключено из автозагрузки: {', '.join(disabled)}"
        return False, "Не удалось отключить ни одной записи (возможно, нужны права администратора)."

    def _rollback_startup(self):
        items = self.opt_backup.get("startup_deleted", [])
        if not items:
            return False, "Нечего восстанавливать (или ничего не удалялось)."
        restored = 0
        if winreg:
            for root, path, name, val, typ in items:
                try:
                    with winreg.OpenKey(root, path, 0, winreg.KEY_SET_VALUE) as k:
                        winreg.SetValueEx(k, name, 0, typ, val)
                        restored += 1
                except Exception:
                    pass
        self.opt_backup["startup_deleted"] = []
        return True, f"Восстановлено записей автозагрузки: {restored}"

    # ----- Mouse -----
    def _get_mouse_accel(self):
        """True = ускорение ОТКЛЮЧЕНО (то что мы хотим при галочке)."""
        if not winreg:
            return None
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Control Panel\Mouse", 0, winreg.KEY_READ) as k:
                speed, _ = winreg.QueryValueEx(k, "MouseSpeed")
                t1, _ = winreg.QueryValueEx(k, "MouseThreshold1")
                t2, _ = winreg.QueryValueEx(k, "MouseThreshold2")
                return str(speed) == "0" and str(t1) == "0" and str(t2) == "0"
        except Exception:
            return None

    def _apply_mouse_settings(self, speed, t1, t2):
        """Пишет в реестр + сразу применяет через SystemParametersInfo."""
        if not winreg:
            return False, "winreg недоступен"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Mouse", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "MouseSpeed", 0, winreg.REG_SZ, str(speed))
            winreg.SetValueEx(key, "MouseThreshold1", 0, winreg.REG_SZ, str(t1))
            winreg.SetValueEx(key, "MouseThreshold2", 0, winreg.REG_SZ, str(t2))
            winreg.CloseKey(key)

            # Применяем сразу (SPI_SETMOUSE = 0x0004)
            class MOUSEPARAMS(ctypes.Structure):
                _fields_ = [
                    ("iMouseThreshold1", ctypes.c_uint),
                    ("iMouseThreshold2", ctypes.c_uint),
                    ("iMouseSpeed", ctypes.c_uint),
                ]

            mp = MOUSEPARAMS(int(t1), int(t2), int(speed))
            SPI_SETMOUSE = 0x0004
            SPIF_UPDATEINIFILE = 0x01
            SPIF_SENDCHANGE = 0x02
            result = ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETMOUSE, 0, ctypes.byref(mp), SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
            )
            if not result:
                # Даже если SPI не сработал — реестр уже записан
                return True, "Записано в реестр (SPI не подтвердил, может потребоваться перелогин)."
            return True, "OK"
        except Exception as e:
            return False, str(e)

    def _apply_mouse_accel(self, disable):
        # Сохраняем старые значения один раз
        if "mouse" not in self.opt_backup and winreg:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Mouse", 0, winreg.KEY_READ) as k:
                    self.opt_backup["mouse"] = {
                        "MouseSpeed": winreg.QueryValueEx(k, "MouseSpeed")[0],
                        "MouseThreshold1": winreg.QueryValueEx(k, "MouseThreshold1")[0],
                        "MouseThreshold2": winreg.QueryValueEx(k, "MouseThreshold2")[0],
                    }
            except Exception:
                self.opt_backup["mouse"] = {"MouseSpeed": "1", "MouseThreshold1": "6", "MouseThreshold2": "10"}

        if disable:
            ok, msg = self._apply_mouse_settings(0, 0, 0)
            if ok:
                return True, "Ускорение мыши ОТКЛЮЧЕНО.\nПроверь в Панель управления → Мышь → Параметры указателя."
            return False, msg
        else:
            # Стандартные значения Windows
            ok, msg = self._apply_mouse_settings(1, 6, 10)
            if ok:
                return True, "Ускорение мыши ВКЛЮЧЕНО (стандартные значения)."
            return False, msg

    def _rollback_mouse_accel(self):
        prev = self.opt_backup.get("mouse")
        if not prev:
            return False, "Нет сохранённого состояния мыши."
        ok, msg = self._apply_mouse_settings(
            prev.get("MouseSpeed", "1"),
            prev.get("MouseThreshold1", "6"),
            prev.get("MouseThreshold2", "10")
        )
        if ok:
            return True, "Параметры мыши восстановлены."
        return False, msg


    # ----- Notifications -----
    def _get_notifications(self):
        if not winreg:
            return None
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\PushNotifications", 0, winreg.KEY_READ) as k:
                val, _ = winreg.QueryValueEx(k, "ToastEnabled")
                return val == 0
        except Exception:
            return None

    def _apply_notifications(self, disable):
        if not winreg:
            return False, "winreg недоступен"
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                   r"Software\Microsoft\Windows\CurrentVersion\PushNotifications")
            winreg.SetValueEx(key, "ToastEnabled", 0, winreg.REG_DWORD, 0 if disable else 1)
            winreg.CloseKey(key)
            return True, f"Уведомления {'отключены' if disable else 'включены'}."
        except Exception as e:
            return False, str(e)

    def _rollback_notifications(self):
        prev = self.opt_backup.get("notifications")
        if prev is None:
            return False, "Нет сохранённого состояния."
        return self._apply_notifications(bool(prev))

    # ----- Rust Priority -----
    def _get_rust_priority(self):
        ok, out, _ = _run_ps(
            "Get-Process -Name 'RustClient','Rust' -ErrorAction SilentlyContinue | "
            "Select-Object -ExpandProperty PriorityClass"
        )
        if not ok or not out:
            return None
        return "High" in out

    def _apply_rust_priority(self, enable):
        if enable:
            ps = r"""
$procs = Get-Process -Name 'RustClient','Rust' -ErrorAction SilentlyContinue
if (-not $procs) { Write-Output 'NO_PROCESS'; exit 1 }
foreach ($p in $procs) {
    $p.PriorityClass = 'High'
    Write-Output "SET:$($p.ProcessName):$($p.Id)"
}
"""
            ok, out, err = _run_ps(ps)
            if "NO_PROCESS" in out:
                return False, "Процесс RustClient.exe / Rust.exe не запущен.\nЗапустите игру и нажмите ПРИМЕНИТЬ снова."
            if ok:
                return True, f"Приоритет установлен в High:\n{out}"
            return False, err or out
        else:
            ps = r"""
$procs = Get-Process -Name 'RustClient','Rust' -ErrorAction SilentlyContinue
foreach ($p in $procs) { $p.PriorityClass = 'Normal' }
Write-Output 'OK'
"""
            ok, out, err = _run_ps(ps)
            return (ok, "Приоритет возвращён в Normal." if ok else err)

    def _rollback_rust_priority(self):
        return self._apply_rust_priority(False)


if __name__ == "__main__":
    if platform.system() == "Windows":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    app = NoaRustTool()
    app.mainloop()
