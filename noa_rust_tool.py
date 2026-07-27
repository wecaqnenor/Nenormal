#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOA RUST TOOL
Тактическая утилита клана NOA (NeNormal / Omperial / Anarchy's)
Модуль: RAM CHECK
"""

import tkinter as tk
from tkinter import ttk
import subprocess
import threading
import sys
import platform
import ctypes

# ============================================================
#   ЦВЕТОВАЯ СХЕМА  —  "холодный / милитаристский / серьёзный"
# ============================================================
COL_BG        = "#0a0a0a"   # почти чёрный фон
COL_PANEL     = "#111111"   # панели чуть светлее
COL_PANEL_2   = "#161616"   # карточки
COL_BORDER    = "#2a2a2a"   # тонкие границы
COL_RED       = "#c81d25"   # основной красный (акцент)
COL_RED_DARK  = "#7a1216"   # тёмно-красный (hover/border)
COL_RED_DIM   = "#3a1013"   # едва тлеющий красный (неактивные элементы)
COL_TEXT      = "#d8d8d8"   # основной текст
COL_TEXT_DIM  = "#7d7d7d"   # приглушённый текст
COL_GREEN     = "#3fae4a"   # статус OK
COL_YELLOW    = "#c8961d"   # статус WARNING
COL_WHITE     = "#f0f0f0"

FONT_MONO   = ("Consolas", 10)
FONT_MONO_B = ("Consolas", 10, "bold")
FONT_TITLE  = ("Consolas", 15, "bold")
FONT_TAB    = ("Consolas", 10, "bold")
FONT_SMALL  = ("Consolas", 9)
FONT_HEAD   = ("Consolas", 11, "bold")


# ============================================================
#   POWERSHELL СКРИПТ ДЛЯ СБОРА ДАННЫХ О ПАМЯТИ
#   (расширенная версия исходного NoaRamCheck.ps1)
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
$slotsMax  = $cs.NumberOfLogicalProcessors
try { $slotsMax = ($cs | Select-Object -ExpandProperty NumberOfProcessors) } catch {}
try {
    $arr = Get-CimInstance Win32_PhysicalMemoryArray
    if ($arr) { $slotsMax = ($arr | Measure-Object MemoryDevices -Sum).Sum }
} catch {}

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
    """Запускает PowerShell-скрипт и парсит вывод. Возвращает dict с результатом."""
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


# ============================================================
#   ВИДЖЕТ: КНОПКА-ВКЛАДКА (стиль "тактический переключатель")
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
#   ГЛАВНОЕ ПРИЛОЖЕНИЕ
# ============================================================
class NoaRustTool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("N O A   R U S T   T O O L")
        self.geometry("1280x700")
        self.resizable(False, False)
        self.configure(bg=COL_BG)

        try:
            self.iconbitmap(default="")
        except Exception:
            pass

        self._build_header()
        self._build_tabbar()
        self._build_body()

        self.tabs = {}
        self._register_tab("ram", "RAM CHECK", self._build_ram_tab)
        self._register_tab("opt", "OPTIMIZATION", self._build_opt_tab)

        self._show_tab("ram")

    # ---------------------------------------------------------
    def _build_header(self):
        header = tk.Frame(self, bg=COL_BG, height=54)
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

        right = tk.Frame(header, bg=COL_BG)
        right.pack(side="right", padx=16)
        tk.Label(right, text="NeNormal \u2022 Omperial \u2022 Anarchy's",
                 font=("Consolas", 8), bg=COL_BG, fg=COL_RED_DARK).pack(anchor="e")
        tk.Label(right, text="TACTICAL CONFIG SUITE",
                 font=("Consolas", 8), bg=COL_BG, fg=COL_TEXT_DIM).pack(anchor="e")

        sep = tk.Frame(self, bg=COL_RED_DARK, height=1)
        sep.pack(side="top", fill="x")

    # ---------------------------------------------------------
    def _build_tabbar(self):
        bar = tk.Frame(self, bg=COL_BG, height=38)
        bar.pack(side="top", fill="x")
        bar.pack_propagate(False)

        self.tab_bar_left = tk.Frame(bar, bg=COL_BG)
        self.tab_bar_left.pack(side="left", padx=16, pady=(6, 0))

        sep = tk.Frame(self, bg=COL_BORDER, height=1)
        sep.pack(side="top", fill="x")

    # ---------------------------------------------------------
    def _build_body(self):
        self.body = tk.Frame(self, bg=COL_BG)
        self.body.pack(side="top", fill="both", expand=True)

    # ---------------------------------------------------------
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

    # ===========================================================
    #   ВКЛАДКА: RAM CHECK
    # ===========================================================
    def _build_ram_tab(self, parent):
        # --- панель управления ---
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

        self.copy_btn = tk.Button(
            btn_frame, text="КОПИРОВАТЬ ОТЧЁТ", font=FONT_MONO, bg=COL_PANEL_2,
            fg=COL_TEXT_DIM, activebackground=COL_PANEL_2, activeforeground=COL_WHITE,
            relief="flat", bd=0, padx=12, pady=8, cursor="hand2",
            command=self._copy_report, state="disabled"
        )
        self.copy_btn.pack(side="left", padx=(8, 0))

        # --- сводная плашка ---
        self.summary_frame = tk.Frame(parent, bg=COL_PANEL, highlightbackground=COL_BORDER,
                                       highlightthickness=1)
        self.summary_frame.pack(side="top", fill="x", padx=16, pady=(0, 10))
        self._build_summary_placeholder()

        # --- область вывода (карточки модулей + статус-баннер) ---
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
        """Крупный статус-баннер вверху списка (OK / WARNING / ERROR)."""
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
        """Карточка одного модуля памяти: заголовок + сетка характеристик."""
        status_color = {"ok": COL_GREEN, "warn": COL_YELLOW, "dim": COL_TEXT_DIM}[status_tag]
        status_text = {"ok": "НОРМА", "warn": "НИЖЕ ЗАЯВЛЕННОЙ", "dim": "НЕ ОПРЕДЕЛЕНО"}[status_tag]

        card = tk.Frame(self.ram_list, bg=COL_PANEL_2, highlightbackground=COL_BORDER,
                         highlightthickness=1)
        card.pack(fill="x", padx=12, pady=5)

        # левая цветная полоска-индикатор
        stripe = tk.Frame(card, bg=status_color, width=4)
        stripe.pack(side="left", fill="y")

        content = tk.Frame(card, bg=COL_PANEL_2)
        content.pack(side="left", fill="both", expand=True, padx=(10, 10), pady=8)

        # строка заголовка: слот + производитель/модель + статус
        head = tk.Frame(content, bg=COL_PANEL_2)
        head.pack(fill="x")
        tk.Label(head, text=f'[{m["slot"]}]', font=FONT_MONO_B, bg=COL_PANEL_2,
                 fg=COL_RED).pack(side="left")
        tk.Label(head, text=f'  {m["manufacturer"]}  \u2022  {m["part"]}',
                 font=FONT_MONO_B, bg=COL_PANEL_2, fg=COL_WHITE).pack(side="left")
        tk.Label(head, text=status_text, font=FONT_SMALL, bg=COL_PANEL_2,
                 fg=status_color).pack(side="right")

        # сетка характеристик
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

        # --- сводная плашка ---
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

        # --- классификация модулей ---
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

        # --- статус-баннер вверху ---
        if slow_count == 0 and unknown_count == 0:
            self.ram_status_lbl.config(text="\u25cf ВСЁ В НОРМЕ", fg=COL_GREEN)
            self._banner("\u2713  ВСЕ МОДУЛИ РАБОТАЮТ НА ЗАЯВЛЕННОЙ ЧАСТОТЕ", COL_GREEN)
        elif slow_count > 0:
            self.ram_status_lbl.config(text="\u25cf ВНИМАНИЕ", fg=COL_YELLOW)
            self._banner(
                f"\u26a0  {slow_count} МОДУЛ(Ь/Я/ЕЙ) НИЖЕ ЗАЯВЛЕННОЙ ЧАСТОТЫ",
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
                     text=f"Примечание: для {unknown_count} модул(я/ей) частота не определена (данные недоступны).",
                     font=FONT_SMALL, bg=COL_PANEL, fg=COL_TEXT_DIM, anchor="w",
                     wraplength=630, justify="left").pack(fill="x", padx=16, pady=(0, 4))

        # --- карточки модулей ---
        for m, tag in classified:
            self._module_card(m, tag)

        tk.Frame(self.ram_list, bg=COL_PANEL, height=8).pack()  # нижний отступ

        # --- текстовый отчёт для копирования ---
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
            report_lines.append(f'ВНИМАНИЕ: {slow_count} модул(ь/я/ей) ниже заявленной частоты. Проверьте XMP/DOCP/EXPO.')
        if unknown_count > 0:
            report_lines.append(f'Примечание: для {unknown_count} модул(я/ей) частота не определена.')

        self._last_report_text = "\n".join(report_lines)
        self.copy_btn.config(state="normal")

    def _copy_report(self):
        if getattr(self, "_last_report_text", ""):
            self.clipboard_clear()
            self.clipboard_append(self._last_report_text)
            self.copy_btn.config(text="СКОПИРОВАНО \u2713")
            self.after(1500, lambda: self.copy_btn.config(text="КОПИРОВАТЬ ОТЧЁТ"))

    # ===========================================================
    #   ВКЛАДКА: OPTIMIZATION  (пока пустая — заглушка)
    # ===========================================================
    def _build_opt_tab(self, parent):
        wrap = tk.Frame(parent, bg=COL_BG)
        wrap.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(wrap, text="\u2699", font=("Consolas", 34),
                 bg=COL_BG, fg=COL_RED_DARK).pack()
        tk.Label(wrap, text="OPTIMIZATION", font=("Consolas", 14, "bold"),
                 bg=COL_BG, fg=COL_WHITE).pack(pady=(6, 2))
        tk.Label(wrap, text="Раздел в разработке", font=FONT_SMALL,
                 bg=COL_BG, fg=COL_TEXT_DIM).pack()


if __name__ == "__main__":
    if platform.system() == "Windows":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    app = NoaRustTool()
    app.mainloop()
