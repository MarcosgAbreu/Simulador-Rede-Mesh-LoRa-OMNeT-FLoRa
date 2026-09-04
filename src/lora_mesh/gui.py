from __future__ import annotations

import queue
import shutil
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Sequence

from .config import SimulationConfig, ValidationError
from .runner import RunResult, run_simulation
from .video import (
    EVENT_DURATION_MS,
    frames_for_playback,
    latest_video,
    open_with_ffplay,
    playback_duration_ms,
)


def fields_to_config(fields: dict[str, Any]) -> SimulationConfig:
    def number(name: str, converter: type[int] | type[float]) -> int | float:
        value = fields.get(name, "")
        try:
            return converter(value)
        except (TypeError, ValueError) as error:
            raise ValidationError(f"campo '{name}' deve ser numérico") from error

    return SimulationConfig(
        node_count=number("nodes", int),
        area_m=number("area_m", float),
        activation_min_s=number("activation_min_s", float),
        activation_max_s=number("activation_max_s", float),
        simulation_time_s=number("simulation_time_s", float),
        seed=number("seed", int),
        initial_message_interval_s=number(
            "initial_message_interval_s", float
        )
        if fields.get("initial_message_interval_s", "") != ""
        else 300.0,
        max_hops=number("max_hops", int)
        if fields.get("max_hops", "") != ""
        else 8,
        max_retries=number("max_retries", int)
        if fields.get("max_retries", "") != ""
        else 2,
        output_dir=Path(fields.get("output_dir", "runs")),
    )


def open_in_file_manager(path: Path) -> None:
    target = Path(path).expanduser().resolve()
    if target.is_file():
        target = target.parent
    if not target.exists():
        raise FileNotFoundError(target)
    wslpath = shutil.which("wslpath")
    explorer = shutil.which("explorer.exe")
    if wslpath and explorer:
        windows_path = subprocess.check_output(
            [wslpath, "-w", str(target)], text=True
        ).strip()
        subprocess.Popen(["explorer.exe", windows_path])
        return
    opener = shutil.which("xdg-open")
    if opener:
        subprocess.Popen(
            [opener, str(target)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    raise RuntimeError(f"não foi possível abrir a pasta {target}")


class VideoPlayerWindow:
    def __init__(
        self,
        parent: tk.Misc,
        frames: Sequence[Path],
        duration_ms: int = EVENT_DURATION_MS,
        title: str = "Vídeo da simulação",
    ) -> None:
        if not frames:
            raise ValueError("não há frames para reproduzir")
        self.frames = [Path(frame) for frame in frames]
        self.duration_ms = duration_ms if duration_ms > 0 else EVENT_DURATION_MS
        self.index = 0
        self.playing = True
        self._job: str | None = None
        self._photo: tk.PhotoImage | None = None
        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.minsize(640, 480)
        self.image_label = ttk.Label(self.top)
        self.image_label.pack(fill="both", expand=True, padx=8, pady=8)
        controls = ttk.Frame(self.top, padding=(8, 0, 8, 8))
        controls.pack(fill="x")
        self.toggle_button = ttk.Button(controls, text="Pausar", command=self._toggle)
        self.toggle_button.pack(side="left")
        ttk.Button(controls, text="Reiniciar", command=self._restart).pack(
            side="left", padx=8
        )
        self.status_label = ttk.Label(controls, text="")
        self.status_label.pack(side="right")
        self.top.protocol("WM_DELETE_WINDOW", self.close)
        self.top.bind("<Escape>", lambda _event: self.close())
        self._show()
        self._job = self.top.after(self.duration_ms, self._tick)

    def close(self) -> None:
        self.playing = False
        if self._job is not None:
            self.top.after_cancel(self._job)
            self._job = None
        self.top.destroy()

    def _toggle(self) -> None:
        self.playing = not self.playing
        self.toggle_button.configure(text="Pausar" if self.playing else "Continuar")
        if self.playing and self._job is None:
            self._job = self.top.after(self.duration_ms, self._tick)

    def _restart(self) -> None:
        self.index = 0
        self.playing = True
        self.toggle_button.configure(text="Pausar")
        self._show()
        if self._job is None:
            self._job = self.top.after(self.duration_ms, self._tick)

    def _tick(self) -> None:
        self._job = None
        if not self.playing:
            return
        if self.index + 1 >= len(self.frames):
            self.playing = False
            self.toggle_button.configure(text="Continuar")
            return
        self.index += 1
        self._show()
        self._job = self.top.after(self.duration_ms, self._tick)

    def _show(self) -> None:
        from PIL import Image, ImageTk

        frame = self.frames[self.index]
        image = Image.open(frame)
        image.thumbnail((960, 720))
        self._photo = ImageTk.PhotoImage(image)
        self.image_label.configure(image=self._photo)
        self.status_label.configure(text=f"{self.index + 1} / {len(self.frames)}")


class SimulationGui:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("IDE — Rede Mesh LoRa AU915")
        self.root.minsize(700, 540)
        self._messages: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._process_thread: threading.Thread | None = None
        self._cancel_event = threading.Event()
        self.entries: dict[str, ttk.Entry] = {}
        self._last_result: RunResult | None = None
        self._player: VideoPlayerWindow | None = None
        self._build()
        self.root.after(100, self._poll_messages)

    def _build(self) -> None:
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)
        ttk.Label(
            container,
            text="Simulação de rede mesh LoRa — AU915",
            font=("TkDefaultFont", 15, "bold"),
        ).pack(anchor="w", pady=(0, 12))

        form = ttk.LabelFrame(container, text="Parâmetros da rede", padding=10)
        form.pack(fill="x")
        fields = [
            ("nodes", "Número de nodos", "10"),
            ("area_m", "Área (lado em metros)", "1000"),
            ("activation_min_s", "Ativação mínima (s)", "0"),
            ("activation_max_s", "Ativação máxima (s)", "3600"),
            ("simulation_time_s", "Tempo máximo simulado (s)", "14400"),
            ("seed", "Semente aleatória", "1"),
            ("initial_message_interval_s", "Intervalo de mensagens (s)", "300"),
            ("max_hops", "Máximo de saltos", "8"),
            ("max_retries", "Máximo de retransmissões", "2"),
        ]
        for row, (key, label, default) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", padx=4, pady=3)
            entry = ttk.Entry(form, width=18)
            entry.insert(0, default)
            entry.grid(row=row, column=1, sticky="ew", padx=4, pady=3)
            self.entries[key] = entry
        form.columnconfigure(1, weight=1)

        output = ttk.Frame(container)
        output.pack(fill="x", pady=10)
        ttk.Label(output, text="Diretório de saída").pack(side="left")
        self.output_entry = ttk.Entry(output)
        self.output_entry.insert(0, "runs")
        self.output_entry.pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(output, text="Escolher", command=self._choose_output).pack(side="right")

        actions = ttk.Frame(container)
        actions.pack(fill="x")
        self.run_button = ttk.Button(actions, text="Executar simulação", command=self._start)
        self.run_button.pack(side="left")
        self.cancel_button = ttk.Button(
            actions, text="Cancelar", command=self._cancel, state="disabled"
        )
        self.cancel_button.pack(side="left", padx=8)
        self.open_video_button = ttk.Button(
            actions, text="Abrir vídeo", command=self._open_video
        )
        self.open_video_button.pack(side="left")
        self.open_dir_button = ttk.Button(
            actions, text="Abrir pasta", command=self._open_output, state="disabled"
        )
        self.open_dir_button.pack(side="left", padx=8)
        self.progress = ttk.Progressbar(actions, mode="indeterminate")
        self.progress.pack(side="right", fill="x", expand=True)

        status_frame = ttk.LabelFrame(container, text="Status e artefatos", padding=8)
        status_frame.pack(fill="both", expand=True, pady=(12, 0))
        self.status = tk.Text(status_frame, height=12, state="disabled", wrap="word")
        self.status.pack(fill="both", expand=True)

    def _choose_output(self) -> None:
        selected = filedialog.askdirectory()
        if selected:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, selected)

    def _fields(self) -> dict[str, str]:
        values = {key: entry.get() for key, entry in self.entries.items()}
        values["output_dir"] = self.output_entry.get()
        return values

    def _write_status(self, text: str) -> None:
        self.status.configure(state="normal")
        self.status.insert(tk.END, text + "\n")
        self.status.see(tk.END)
        self.status.configure(state="disabled")

    def _start(self) -> None:
        try:
            config = fields_to_config(self._fields())
        except ValidationError as error:
            messagebox.showerror("Parâmetros inválidos", str(error))
            return
        self._cancel_event.clear()
        self.run_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.progress.start(12)
        self._write_status("Iniciando simulação...")
        self._process_thread = threading.Thread(
            target=self._worker, args=(config,), daemon=True
        )
        self._process_thread.start()

    def _worker(self, config: SimulationConfig) -> None:
        try:
            result = run_simulation(config, self._cancel_event)
            self._messages.put(("result", result))
        except Exception as error:  # noqa: BLE001
            self._messages.put(("error", str(error)))

    def _cancel(self) -> None:
        self._cancel_event.set()
        self._write_status("Cancelamento solicitado; aguarde o processo terminar.")

    def _video_target(self) -> Path | None:
        if self._last_result and self._last_result.video_path:
            return Path(self._last_result.video_path)
        output_root = Path(self.output_entry.get() or "runs")
        return latest_video(output_root)

    def _open_output(self) -> None:
        target = (
            Path(self._last_result.output_dir)
            if self._last_result
            else Path(self.output_entry.get() or "runs")
        )
        try:
            open_in_file_manager(target)
        except Exception as error:  # noqa: BLE001
            messagebox.showerror("Falha ao abrir pasta", str(error))

    def _open_video(self) -> None:
        target = self._video_target()
        if target is None or not target.exists():
            selected = filedialog.askopenfilename(
                title="Abrir vídeo MPEG",
                initialdir=str(Path(self.output_entry.get() or "runs")),
                filetypes=[("MPEG", "*.mpg *.mpeg"), ("Todos os arquivos", "*.*")],
            )
            if not selected:
                return
            target = Path(selected)
        self._play_video(target)

    def _play_video(self, target: Path) -> None:
        frames = frames_for_playback(target)
        if frames:
            if self._player is not None:
                try:
                    self._player.close()
                except tk.TclError:
                    pass
            self._player = VideoPlayerWindow(
                self.root,
                frames,
                duration_ms=playback_duration_ms(target),
                title=f"Vídeo — {target}",
            )
            return
        if target.is_file():
            try:
                open_with_ffplay(target)
                return
            except Exception as error:  # noqa: BLE001
                messagebox.showerror("Falha ao abrir vídeo", str(error))
                return
        messagebox.showerror(
            "Vídeo indisponível",
            "Não há frames nem arquivo MPEG para reproduzir.",
        )

    def _poll_messages(self) -> None:
        try:
            while True:
                kind, value = self._messages.get_nowait()
                self.progress.stop()
                self.run_button.configure(state="normal")
                self.cancel_button.configure(state="disabled")
                if kind == "error":
                    self._write_status(f"ERRO: {value}")
                    messagebox.showerror("Falha", value)
                else:
                    result: RunResult = value
                    self._last_result = result
                    self.open_dir_button.configure(state="normal")
                    self._write_status(f"Saída: {result.output_dir}")
                    self._write_status(f"Logs: {result.events_path}")
                    self._write_status(f"Relatório: {result.report_path}")
                    self._write_status(f"Vídeo: {result.video_path or 'não gerado'}")
                    if result.success and result.video_path:
                        self._play_video(Path(result.video_path))
                    elif not result.success:
                        self._write_status(
                            "Vídeo não gerado porque a simulação não concluiu."
                        )
        except queue.Empty:
            pass
        self.root.after(100, self._poll_messages)


def main() -> None:
    root = tk.Tk()
    SimulationGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
