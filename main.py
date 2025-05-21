import os
import asyncio
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog, scrolledtext
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.types import Channel, Chat
from telethon.errors import ChannelInvalidError, SessionPasswordNeededError
import configparser

class TelegramVideoDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Telegram Video Downloader Pro")
        self.root.geometry("700x650")
        
        self.session_file = "tg_session.session"
        self.config_file = "config.ini"
        self.log_file = "download_log.txt"
        self.download_folder = None
        
        self.is_downloading = False
        self.current_progress = 0
        self.start_time = None
        self._setup_gui()
        self._load_config()
        self._check_existing_session()

    def _setup_gui(self):
        """Initializing GUI / Инициализация графического интерфейса""" # You need to select the desired language / необходимо выбрать нужный язык
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        auth_frame = ttk.LabelFrame(main_frame, text="1. Authorization / Авторизация", padding=10)
        auth_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(auth_frame, text="API ID:").grid(row=0, column=0, sticky=tk.W)
        self.api_id_entry = ttk.Entry(auth_frame)
        self.api_id_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        
        ttk.Label(auth_frame, text="API HASH:").grid(row=1, column=0, sticky=tk.W)
        self.api_hash_entry = ttk.Entry(auth_frame)
        self.api_hash_entry.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)
        
        self.auth_btn = ttk.Button(
            auth_frame,
            text="Log in / Авторизоваться",
            command=self._start_auth
        )
        self.auth_btn.grid(row=2, columnspan=2, pady=5)

        download_frame = ttk.LabelFrame(main_frame, text="2. Download Parameters / Параметры загрузки", padding=10)
        download_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(download_frame, text="Message range / Диапазон сообщений:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(download_frame, text="From (inclusive) / От (включительно):").grid(row=1, column=0, sticky=tk.W)
        self.from_msg_entry = ttk.Entry(download_frame, width=10)
        self.from_msg_entry.grid(row=1, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(download_frame, text="Up to (inclusive) / До (включительно):").grid(row=1, column=2, sticky=tk.W)
        self.to_msg_entry = ttk.Entry(download_frame, width=10)
        self.to_msg_entry.grid(row=1, column=3, sticky=tk.W, padx=5)
        
        ttk.Label(download_frame, text="Size limit (GB) / Лимит размера (ГБ):").grid(row=2, column=0, sticky=tk.W)
        self.size_limit_entry = ttk.Entry(download_frame, width=10)
        self.size_limit_entry.insert(0, "5")
        self.size_limit_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(download_frame, text="Channel (name or link) / Канал (имя или ссылка):").grid(row=3, column=0, sticky=tk.W)
        self.channel_entry = ttk.Entry(download_frame)
        self.channel_entry.grid(row=3, column=1, columnspan=3, sticky=tk.EW, padx=5, pady=2)
        
        ttk.Label(download_frame, text="Folder to save / Папка для сохранения:").grid(row=4, column=0, sticky=tk.W)
        self.folder_btn = ttk.Button(
            download_frame,
            text="Выбрать",
            command=self._select_folder,
            width=10
        )
        self.folder_btn.grid(row=4, column=1, sticky=tk.W, padx=5)
        self.folder_label = ttk.Label(download_frame, text="Not selected / Не выбрана", foreground="gray")
        self.folder_label.grid(row=4, column=2, columnspan=2, sticky=tk.W)

        progress_frame = ttk.LabelFrame(main_frame, text="3. Download progress / Прогресс загрузки", padding=10)
        progress_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Прогресс-бар
        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        # Лог в реальном времени
        self.log_text = scrolledtext.ScrolledText(progress_frame, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # Кнопка загрузки
        self.download_btn = ttk.Button(
            main_frame,
            text="Начать загрузку",
            command=self._start_download,
            state=tk.DISABLED
        )
        self.download_btn.pack(pady=10)

    def _load_config(self):
        """Загрузка сохраненных API данных из конфиг-файла"""
        config = configparser.ConfigParser()
        if os.path.exists(self.config_file):
            config.read(self.config_file)
            if 'Telegram' in config:
                self.api_id_entry.insert(0, config['Telegram'].get('api_id', ''))
                self.api_hash_entry.insert(0, config['Telegram'].get('api_hash', ''))

    def _save_config(self):
        """Сохранение API данных в конфиг-файл"""
        config = configparser.ConfigParser()
        config['Telegram'] = {
            'api_id': self.api_id_entry.get(),
            'api_hash': self.api_hash_entry.get()
        }
        with open(self.config_file, 'w') as f:
            config.write(f)

    def _check_existing_session(self):
        """Проверка существующей сессии Telegram"""
        if os.path.exists(self.session_file):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                with TelegramClient(self.session_file, 0, "", loop=loop) as client:
                    if client.is_user_authorized():
                        self.client = client
                        self._update_ui(authorized=True)
                        self._log("Обнаружена сохраненная сессия")
            except Exception as e:
                self._log(f"Ошибка проверки сессии: {str(e)}")

    def _start_auth(self):
        """Запуск процесса авторизации"""
        api_id = self.api_id_entry.get().strip()
        api_hash = self.api_hash_entry.get().strip()
        
        if not api_id or not api_hash:
            messagebox.showerror("Ошибка", "Введите API ID и HASH")
            return
        
        try:
            api_id = int(api_id)
        except ValueError:
            messagebox.showerror("Ошибка", "API ID должен быть числом")
            return
        
        # Сохраняем API данные
        self._save_config()
        
        # Запускаем авторизацию в отдельном потоке
        threading.Thread(target=self._auth_thread, daemon=True).start()

    def _auth_thread(self):
        """Поток для выполнения авторизации"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            with TelegramClient(
                self.session_file,
                int(self.api_id_entry.get()),
                self.api_hash_entry.get(),
                loop=loop
            ) as client:
                if not client.is_user_authorized():
                    phone = self._get_input("Введите номер телефона (с кодом страны):")
                    if not phone:
                        return
                    
                    client.loop.run_until_complete(client.send_code_request(phone))
                    code = self._get_input("Введите код из Telegram:")
                    if not code:
                        return
                    
                    try:
                        client.loop.run_until_complete(client.sign_in(phone, code))
                    except SessionPasswordNeededError:
                        password = self._get_input("Введите пароль 2FA:", show="*")
                        if not password:
                            return
                        client.loop.run_until_complete(client.sign_in(password=password))
                
                self.client = client
                self.root.after(0, lambda: self._update_ui(authorized=True))
                self._log("Авторизация успешно завершена")
                
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка авторизации", str(e)))
            self._log(f"Ошибка авторизации: {str(e)}")

    def _get_input(self, prompt, show=None):
        """Вспомогательная функция для получения ввода через GUI"""
        result = []
        def get():
            result.append(simpledialog.askstring("Ввод", prompt, show=show))
        self.root.after(0, get)
        while not result:
            self.root.update()
        return result[0]

    def _update_ui(self, authorized):
        """Обновление интерфейса после авторизации"""
        if authorized:
            self.download_btn.config(state=tk.NORMAL)
            self.auth_btn.config(text="Авторизовано", state=tk.DISABLED)
        else:
            self.download_btn.config(state=tk.DISABLED)
            self.auth_btn.config(text="Авторизоваться")

    def _select_folder(self):
        """Выбор папки для сохранения видео"""
        folder = filedialog.askdirectory()
        if folder:
            self.download_folder = folder
            self.folder_label.config(text=folder)

    def _start_download(self):
        """Запуск процесса загрузки с проверкой параметров"""
        if not self.download_folder:
            messagebox.showerror("Ошибка", "Выберите папку для сохранения")
            return
            
        channel = self.channel_entry.get().strip()
        if not channel:
            messagebox.showerror("Ошибка", "Введите имя канала")
            return
        
        try:
            from_msg = int(self.from_msg_entry.get()) if self.from_msg_entry.get() else None
            to_msg = int(self.to_msg_entry.get()) if self.to_msg_entry.get() else None
        except ValueError:
            messagebox.showerror("Ошибка", "Номера сообщений должны быть числами")
            return
        
        try:
            size_limit_gb = float(self.size_limit_entry.get())
            size_limit_bytes = int(size_limit_gb * 1024**3)  # Конвертируем в байты
        except ValueError:
            messagebox.showerror("Ошибка", "Лимит размера должен быть числом")
            return
        
        # Подготовка интерфейса к загрузке
        self.is_downloading = True
        self.start_time = datetime.now()
        self.progress_bar['value'] = 0
        self._log("\n=== НАЧАЛО ЗАГРУЗКИ ===")
        self._log(f"Время начала: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self._log(f"Канал: {channel}")
        self._log(f"Диапазон сообщений: {from_msg or 'начало'} - {to_msg or 'конец'}")
        self._log(f"Лимит размера: {size_limit_gb} ГБ")
        
        # Запуск загрузки в отдельном потоке
        threading.Thread(
            target=self._download_thread,
            args=(channel, from_msg, to_msg, size_limit_bytes),
            daemon=True
        ).start()

    def _download_thread(self, channel, from_msg, to_msg, size_limit_bytes):
        """Поток для выполнения загрузки"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            with TelegramClient(
                self.session_file,
                int(self.api_id_entry.get()),
                self.api_hash_entry.get(),
                loop=loop
            ) as client:
                loop.run_until_complete(
                    self._download_videos(client, channel, from_msg, to_msg, size_limit_bytes)
                )
                
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка загрузки", str(e)))
            self._log(f"ОШИБКА: {str(e)}")
        finally:
            self.is_downloading = False
            duration = datetime.now() - self.start_time
            self._log(f"\n=== ЗАВЕРШЕНО ===")
            self._log(f"Общее время: {duration}")
            self.root.after(0, lambda: self.progress_bar.stop())

    async def _download_videos(self, client, channel, from_msg, to_msg, size_limit_bytes):
        """Основная логика загрузки видео"""
        try:
            # Нормализация имени канала
            channel = channel.strip()
            if channel.startswith("https://t.me/"):
                channel = channel.split("/")[-1]
            if channel.startswith("@"):
                channel = channel[1:]

            # Получаем entity канала
            try:
                entity = await client.get_entity(channel)
            except (ValueError, ChannelInvalidError):
                self.root.after(0, lambda: messagebox.showerror("Ошибка", "Канал не найден"))
                self._log("ОШИБКА: Канал не найден")
                return

            if not isinstance(entity, (Channel, Chat)):
                self.root.after(0, lambda: messagebox.showerror("Ошибка", "Это не канал или чат"))
                self._log("ОШИБКА: Это не канал или чат")
                return

            # Создаем папку и лог-файл
            os.makedirs(self.download_folder, exist_ok=True)
            log_path = os.path.join(self.download_folder, self.log_file)
            
            total_size = 0
            downloaded_count = 0
            first_msg_id = None
            last_msg_id = None
            size_exceeded = False

            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"=== Загрузка из {channel} ===\n")
                f.write(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Диапазон сообщений: {from_msg or 'начало'} - {to_msg or 'конец'}\n")
                f.write(f"Лимит размера: {size_limit_bytes/1024**3:.2f} ГБ\n\n")
                
                # Получаем общее количество сообщений для прогресс-бара
                total_messages = await client.get_messages(
                    entity,
                    limit=1,
                    min_id=from_msg,
                    max_id=to_msg
                )
                total_count = total_messages.total if hasattr(total_messages, 'total') else 0
                
                # Итерируемся по сообщениям в указанном диапазоне (включительно)
                async for message in client.iter_messages(
                    entity,
                    min_id=from_msg-1 if from_msg else None,  # Коррекция для включения нижней границы
                    max_id=to_msg,
                    reverse=True
                ):
                    if not self.is_downloading:
                        self._log("Загрузка прервана пользователем")
                        break
                        
                    if message.video:
                        try:
                            file_size = message.file.size if message.file else 0
                            
                            # Проверка лимита размера
                            if total_size + file_size > size_limit_bytes:
                                size_exceeded = True
                                self._log(f"Достигнут лимит размера! ({total_size/1024**3:.2f}/{size_limit_bytes/1024**3:.2f} ГБ)")
                                f.write(f"\nДостигнут лимит размера! Скачано {downloaded_count} видео\n")
                                break
                            
                            # Скачивание файла
                            start_time = datetime.now()
                            filename = f"{message.id}.mp4"
                            path = os.path.join(self.download_folder, filename)
                            
                            await message.download_media(
                                file=path,
                                progress_callback=lambda c, t: self._update_progress(message.id, c, t)
                            )
                            
                            # Обновление статистики
                            download_time = (datetime.now() - start_time).total_seconds()
                            speed = file_size / (1024 * 1024 * download_time) if download_time > 0 else 0
                            
                            total_size += file_size
                            downloaded_count += 1
                            last_msg_id = last_msg_id or message.id
                            first_msg_id = message.id
                            
                            # Запись в лог-файл
                            log_line = (
                                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                                f"ID: {message.id} | "
                                f"Размер: {file_size/1024**2:.2f} MB | "
                                f"Скорость: {speed:.2f} MB/s | "
                                f"Файл: {filename}\n"
                            )
                            f.write(log_line)
                            
                            # Обновление интерфейса
                            self._log(
                                f"Скачано: {filename} | "
                                f"{file_size/1024**2:.2f} MB | "
                                f"{speed:.2f} MB/s"
                            )
                            
                            # Обновление прогресс-бара
                            if total_count > 0:
                                progress = (downloaded_count / total_count) * 100
                                self.root.after(0, lambda: self.progress_bar.config(value=progress))
                            
                        except Exception as e:
                            self._log(f"Ошибка при скачивании {message.id}: {str(e)}")
                            f.write(f"Ошибка: {message.id} - {str(e)}\n")

                # Запись итогов
                f.write("\n=== Итоги ===\n")
                f.write(f"Скачано видео: {downloaded_count}\n")
                f.write(f"Общий размер: {total_size/1024**3:.2f} ГБ\n")
                if first_msg_id and last_msg_id:
                    f.write(f"Диапазон сообщений: {first_msg_id} - {last_msg_id}\n")
                if size_exceeded:
                    f.write("Внимание: достигнут лимит по размеру!\n")
                f.write(f"Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

            # Итоговое сообщение
            result_msg = [
                f"Загрузка завершена!",
                f"Скачано видео: {downloaded_count}",
                f"Общий размер: {total_size/1024**3:.2f} ГБ",
            ]
            if first_msg_id and last_msg_id:
                result_msg.append(f"Диапазон сообщений: {first_msg_id}-{last_msg_id}")
            if size_exceeded:
                result_msg.append("Внимание: достигнут лимит по размеру!")
            
            self.root.after(0, lambda: messagebox.showinfo(
                "Готово",
                "\n".join(result_msg)
            ))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
            self._log(f"КРИТИЧЕСКАЯ ОШИБКА: {str(e)}")

    def _update_progress(self, msg_id, current, total):
        """Обновление прогресса загрузки текущего файла"""
        if total > 0:
            percent = (current / total) * 100
            self.root.after(0, lambda: self.progress_bar.config(
                value=percent,
                style="green.Horizontal.TProgressbar" if percent < 100 else "blue.Horizontal.TProgressbar"
            ))

    def _log(self, message):
        """Добавление сообщения в лог"""
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        full_message = f"{timestamp} {message}\n"
        
        self.root.after(0, lambda: self._update_log_display(full_message))
        
        # Также записываем в файл лога в папке загрузки
        if self.download_folder:
            log_path = os.path.join(self.download_folder, self.log_file)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(full_message)

    def _update_log_display(self, message):
        """Обновление лога в интерфейсе"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)


if __name__ == "__main__":
    root = tk.Tk()
    
    # Центрирование окна
    window_width = 700
    window_height = 650
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    # Стили для прогресс-бара
    style = ttk.Style()
    style.configure("green.Horizontal.TProgressbar", foreground='green', background='green')
    style.configure("blue.Horizontal.TProgressbar", foreground='blue', background='blue')
    
    app = TelegramVideoDownloader(root)
    root.mainloop()
