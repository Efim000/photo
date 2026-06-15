import csv
import os
import subprocess
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog, ttk

try:
    import customtkinter as ctk
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "Не найден customtkinter. Запустите через .venv или установите: pip install customtkinter"
    ) from exc

from database import Database

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_BG = "#0E1117"
CARD_BG = "#161B22"
ACCENT = "#3B82F6"
ACCENT_HOVER = "#2563EB"
SECONDARY = "#22C55E"
TEXT_MAIN = "#F8FAFC"
TEXT_MUTED = "#94A3B8"
FONT_FAMILY = ("Segoe UI", 12)
TAG_FONT = ("Segoe UI", 11, "italic")


class LoginApp:
    """Окно авторизации и регистрации."""

    def __init__(self, root, db):
        self.root = root
        self.db = db
        self.root.title("Авторизация")
        self.root.geometry("450x340")
        self.root.resizable(False, False)
        self.root.configure(fg_color=APP_BG)

        self.frame = ctk.CTkFrame(self.root, fg_color=CARD_BG, corner_radius=16)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            self.frame,
            text="Вход в систему",
            font=("Segoe UI", 22, "bold"),
            text_color=TEXT_MAIN,
        ).pack(pady=(20, 18))

        ctk.CTkLabel(self.frame, text="Логин", text_color=TEXT_MUTED).pack(anchor="w", padx=24)
        self.entry_login = ctk.CTkEntry(
            self.frame,
            width=360,
            placeholder_text="Введите логин",
        )
        self.entry_login.pack(padx=24, pady=(6, 12))

        ctk.CTkLabel(self.frame, text="Пароль", text_color=TEXT_MUTED).pack(anchor="w", padx=24)
        self.entry_password = ctk.CTkEntry(
            self.frame,
            width=360,
            show="*",
            placeholder_text="Введите пароль",
        )
        self.entry_password.pack(padx=24, pady=(6, 18))

        btn_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        btn_frame.pack(pady=(0, 20))
        ctk.CTkButton(
            btn_frame,
            text="Войти",
            width=170,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            command=self.login,
        ).pack(side=tk.LEFT, padx=6)
        ctk.CTkButton(
            btn_frame,
            text="Регистрация",
            width=170,
            fg_color=SECONDARY,
            hover_color="#16A34A",
            command=self.register,
        ).pack(side=tk.LEFT, padx=6)

        self.entry_login.focus()
        self.root.bind("<Return>", lambda e: self.login())

    def login(self):
        login = self.entry_login.get().strip()
        password = self.entry_password.get()
        if not login or not password:
            messagebox.showwarning("Ошибка", "Введите логин и пароль")
            return
        user = self.db.authenticate(login, password)
        if user:
            self.root.destroy()
            root_main = ctk.CTk()
            MainApp(root_main, self.db, user)
            root_main.mainloop()
        else:
            messagebox.showerror("Ошибка", "Неверный логин или пароль")

    def register(self):
        login = self.entry_login.get().strip()
        password = self.entry_password.get()
        if not login or not password:
            messagebox.showwarning("Ошибка", "Введите логин и пароль")
            return
        if self.db.register_user(login, password):
            messagebox.showinfo("Успех", "Пользователь зарегистрирован. Теперь войдите.")
            self.entry_login.delete(0, tk.END)
            self.entry_password.delete(0, tk.END)
        else:
            messagebox.showerror("Ошибка", "Пользователь с таким логином уже существует")


class MainApp:
    """Главное окно приложения."""

    def __init__(self, root, db, user):
        self.root = root
        self.db = db
        self.user = user
        self.current_tag_filter = None
        self.current_start_date = None
        self.current_end_date = None

        self.root.title("Коллекция фотографий")
        self.root.geometry("1100x760")
        self.root.configure(fg_color=APP_BG)

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure(
            "Treeview",
            font=FONT_FAMILY,
            rowheight=30,
            background="#0F172A",
            foreground="#E2E8F0",
            fieldbackground="#0F172A",
        )
        self.style.map("Treeview", background=[("selected", "#1D4ED8")])
        self.style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"), background="#1E293B", foreground="#F8FAFC")

        self.create_menu()

        self.main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.notebook = ctk.CTkTabview(self.main_frame, fg_color=CARD_BG, segmented_button_fg_color="#1F2937")
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_add = self.notebook.add("Добавить фото")
        self.tab_catalog = self.notebook.add("Каталог")
        self.tab_tags = self.notebook.add("Теги")

        self.build_add_tab()
        self.build_catalog_tab()
        self.build_tags_tab()

        self.root.bind("<Control-n>", lambda e: self.new_record())
        self.root.bind("<Control-o>", lambda e: self.open_file_from_catalog())

        self.refresh_catalog()
        self.refresh_tags()

        if self.user["role"] == "admin":
            self.add_admin_menu()

    def create_menu(self):
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)

        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Новая запись", command=self.new_record, accelerator="Ctrl+N")
        file_menu.add_command(label="Удалить", command=self.delete_selected_photo)
        file_menu.add_command(label="Экспорт в CSV", command=self.export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit)

        search_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Поиск", menu=search_menu)
        search_menu.add_command(label="По тегам", command=self.search_by_tag)
        search_menu.add_command(label="По дате", command=self.search_by_date)
        search_menu.add_separator()
        search_menu.add_command(label="Сбросить фильтр", command=self.reset_filters)

        help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="О программе", command=self.about)

    def add_admin_menu(self):
        """Добавляет пункт меню для администратора."""
        admin_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Администрирование", menu=admin_menu)
        admin_menu.add_command(label="Управление пользователями", command=self.manage_users)

    def manage_users(self):
        """Окно управления пользователями (только для админа)."""
        win = ctk.CTkToplevel(self.root)
        win.title("Управление пользователями")
        win.geometry("600x400")
        win.transient(self.root)
        win.grab_set()
        win.configure(fg_color=CARD_BG)

        columns = ("ID", "Логин", "Роль")
        tree_container = ctk.CTkFrame(win, fg_color="#0F172A")
        tree_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        tree = ttk.Treeview(tree_container, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        def refresh_users():
            for item in tree.get_children():
                tree.delete(item)
            users = self.db.get_all_users()
            for u in users:
                tree.insert("", tk.END, values=(u["id"], u["username"], u["role"]))

        refresh_users()

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(pady=5)

        def delete_user():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Предупреждение", "Выберите пользователя")
                return
            values = tree.item(selected[0])["values"]
            user_id = values[0]
            username = values[1]
            if username == "admin" or user_id == self.user["id"]:
                messagebox.showerror("Ошибка", "Нельзя удалить администратора или самого себя")
                return
            if messagebox.askyesno("Подтверждение", f"Удалить пользователя '{username}'? Все его фотографии будут удалены."):
                self.db.delete_user(user_id)
                refresh_users()
                if user_id == self.user["id"]:
                    messagebox.showinfo("Информация", "Ваша учётная запись удалена. Приложение будет закрыто.")
                    self.root.quit()

        def reset_password():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Предупреждение", "Выберите пользователя")
                return
            values = tree.item(selected[0])["values"]
            user_id = values[0]
            username = values[1]
            new_pass = simpledialog.askstring("Сброс пароля", f"Введите новый пароль для {username}:", show="*")
            if new_pass and len(new_pass) > 0:
                self.db.reset_password(user_id, new_pass)
                messagebox.showinfo("Успех", "Пароль изменён")
            elif new_pass == "":
                messagebox.showwarning("Ошибка", "Пароль не может быть пустым")

        ctk.CTkButton(btn_frame, text="Удалить", command=delete_user, fg_color="#DC2626", hover_color="#B91C1C").pack(
            side=tk.LEFT, padx=5
        )
        ctk.CTkButton(btn_frame, text="Сбросить пароль", command=reset_password, fg_color=ACCENT, hover_color=ACCENT_HOVER).pack(
            side=tk.LEFT, padx=5
        )

    def build_add_tab(self):
        frame = self.tab_add
        ctk.CTkLabel(frame, text="Название фото (обязательно):", text_color=TEXT_MAIN).grid(
            row=0, column=0, sticky=tk.W, padx=14, pady=8
        )
        self.title_entry = ctk.CTkEntry(frame, width=500, placeholder_text="Например: Закат у моря")
        self.title_entry.grid(row=0, column=1, padx=10, pady=5)

        ctk.CTkLabel(frame, text="Описание:", text_color=TEXT_MAIN).grid(row=1, column=0, sticky=tk.W, padx=14, pady=8)
        self.desc_text = ctk.CTkTextbox(frame, height=120, width=500, font=FONT_FAMILY)
        self.desc_text.grid(row=1, column=1, padx=10, pady=5)

        ctk.CTkLabel(frame, text="Дата съёмки (ГГГГ-ММ-ДД):", text_color=TEXT_MAIN).grid(
            row=2, column=0, sticky=tk.W, padx=14, pady=8
        )
        self.date_entry = ctk.CTkEntry(frame, width=220, placeholder_text="2026-04-08")
        self.date_entry.grid(row=2, column=1, sticky=tk.W, padx=10, pady=5)

        ctk.CTkLabel(frame, text="Путь к файлу:", text_color=TEXT_MAIN).grid(row=3, column=0, sticky=tk.W, padx=14, pady=8)
        path_frame = ctk.CTkFrame(frame, fg_color="transparent")
        path_frame.grid(row=3, column=1, sticky=tk.W, padx=10, pady=5)
        self.path_entry = ctk.CTkEntry(path_frame, width=410, placeholder_text="Выберите файл изображения")
        self.path_entry.pack(side=tk.LEFT)
        ctk.CTkButton(path_frame, text="Обзор...", command=self.browse_file, width=90, fg_color=ACCENT, hover_color=ACCENT_HOVER).pack(
            side=tk.LEFT, padx=5
        )

        ctk.CTkLabel(frame, text="Теги (через запятую):", text_color=TEXT_MAIN).grid(
            row=4, column=0, sticky=tk.W, padx=14, pady=8
        )
        self.tags_entry = ctk.CTkEntry(frame, width=500, placeholder_text="travel, beach, sunset")
        self.tags_entry.grid(row=4, column=1, padx=10, pady=5)

        ctk.CTkLabel(frame, text="Категория:", text_color=TEXT_MAIN).grid(row=5, column=0, sticky=tk.W, padx=14, pady=8)
        self.category_combo = ctk.CTkComboBox(
            frame,
            values=["Путешествия", "Семья", "Природа", "События"],
            width=250,
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
        )
        self.category_combo.grid(row=5, column=1, sticky=tk.W, padx=10, pady=5)
        self.category_combo.set("Путешествия")

        ctk.CTkButton(
            frame,
            text="Сохранить запись",
            command=self.save_photo,
            fg_color=SECONDARY,
            hover_color="#16A34A",
            width=230,
        ).grid(row=6, column=1, sticky=tk.W, padx=10, pady=20)

    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Выберите изображение",
            filetypes=[("Изображения", "*.jpg *.jpeg *.png *.gif *.bmp"), ("Все файлы", "*.*")]
        )
        if filename:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, filename)

    def save_photo(self):
        title = self.title_entry.get().strip()
        description = self.desc_text.get("1.0", tk.END).strip()
        date_taken = self.date_entry.get().strip()
        file_path = self.path_entry.get().strip()
        tags = self.tags_entry.get().strip()
        category = self.category_combo.get()

        if not title:
            messagebox.showwarning("Ошибка", "Название фото обязательно")
            return
        if not file_path:
            messagebox.showwarning("Ошибка", "Путь к файлу обязателен")
            return
        if not os.path.exists(file_path):
            messagebox.showerror("Ошибка", "Файл не найден по указанному пути")
            return
        try:
            datetime.strptime(date_taken, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Ошибка", "Дата должна быть в формате ГГГГ-ММ-ДД")
            return

        self.db.add_photo(self.user["id"], title, description, date_taken, file_path, tags, category)
        messagebox.showinfo("Успех", "Фотография добавлена")
        self.clear_add_form()
        self.refresh_catalog()
        self.refresh_tags()

    def clear_add_form(self):
        self.title_entry.delete(0, tk.END)
        self.desc_text.delete("1.0", tk.END)
        self.date_entry.delete(0, tk.END)
        self.path_entry.delete(0, tk.END)
        self.tags_entry.delete(0, tk.END)
        self.category_combo.set("Путешествия")

    def build_catalog_tab(self):
        frame = self.tab_catalog
        tree_frame = ctk.CTkFrame(frame, fg_color="#0F172A")
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("id", "title", "date_taken", "category", "tags_preview")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        self.tree.heading("id", text="ID")
        self.tree.heading("title", text="Название")
        self.tree.heading("date_taken", text="Дата")
        self.tree.heading("category", text="Категория")
        self.tree.heading("tags_preview", text="Теги")
        self.tree.column("id", width=50)
        self.tree.column("title", width=200)
        self.tree.column("date_taken", width=100)
        self.tree.column("category", width=120)
        self.tree.column("tags_preview", width=250)

        vsb = ctk.CTkScrollbar(tree_frame, orientation="vertical", command=self.tree.yview)
        hsb = ctk.CTkScrollbar(tree_frame, orientation="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        for col in columns:
            self.tree.heading(col, command=lambda c=col: self.sort_by_column(c, False))

        self.tree.bind("<Double-1>", self.show_details)

        self.tree.bind("<Delete>", lambda e: self.delete_selected_photo())

        self.tree.tag_configure("italic", font=TAG_FONT)

    def refresh_catalog(self):
        """Обновляет таблицу каталога с учётом текущих фильтров."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        photos = self.db.get_photos(
            self.user["id"],
            tag_filter=self.current_tag_filter,
            start_date=self.current_start_date,
            end_date=self.current_end_date
        )
        for p in photos:
            tags_value = p.get("tags") or ""
            tags_preview = tags_value[:30] + ("..." if len(tags_value) > 30 else "")
            values = (p["id"], p["title"], p["date_taken"], p["category"], tags_preview)
            item_id = self.tree.insert("", tk.END, values=values)
            self.tree.item(item_id, tags=("italic",))

    def sort_by_column(self, col, reverse):
        """Сортировка данных в Treeview."""
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children("")]
        if col == "id":
            data.sort(key=lambda x: int(x[0]), reverse=reverse)
        if col == "date_taken":
            data.sort(key=lambda x: x[0], reverse=reverse)
        elif col != "id":
            data.sort(key=lambda x: x[0].lower(), reverse=reverse)
        for index, (_, child) in enumerate(data):
            self.tree.move(child, "", index)
        self.tree.heading(col, command=lambda: self.sort_by_column(col, not reverse))

    def delete_selected_photo(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите запись для удаления")
            return
        item = selected[0]
        photo_id = self.tree.item(item, "values")[0]
        if messagebox.askyesno("Подтверждение", "Удалить выбранную фотографию?"):
            self.db.delete_photo(int(photo_id), self.user["id"])
            self.refresh_catalog()
            self.refresh_tags()

    def show_details(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        item = selected[0]
        photo_id = int(self.tree.item(item, "values")[0])
        photo = self.db.get_photo_by_id(photo_id, self.user["id"])
        if not photo:
            messagebox.showerror("Ошибка", "Фотография не найдена")
            return

        win = ctk.CTkToplevel(self.root)
        win.title(f"Карточка фото: {photo['title']}")
        win.geometry("500x400")
        win.transient(self.root)
        win.grab_set()
        win.configure(fg_color=CARD_BG)

        ctk.CTkLabel(win, text=f"Название: {photo['title']}", text_color=TEXT_MAIN).pack(anchor=tk.W, padx=10, pady=3)
        ctk.CTkLabel(win, text=f"Описание: {photo['description']}", text_color=TEXT_MAIN).pack(anchor=tk.W, padx=10, pady=3)
        ctk.CTkLabel(win, text=f"Дата: {photo['date_taken']}", text_color=TEXT_MAIN).pack(anchor=tk.W, padx=10, pady=3)
        ctk.CTkLabel(win, text=f"Категория: {photo['category']}", text_color=TEXT_MAIN).pack(anchor=tk.W, padx=10, pady=3)
        ctk.CTkLabel(win, text=f"Теги: {photo['tags']}", text_color=TEXT_MAIN).pack(anchor=tk.W, padx=10, pady=3)
        ctk.CTkLabel(win, text=f"Путь: {photo['file_path']}", text_color=TEXT_MUTED).pack(anchor=tk.W, padx=10, pady=3)

        def open_file():
            path = photo["file_path"]
            if os.path.exists(path):
                if os.name == 'nt':
                    os.startfile(path)
                else:
                    subprocess.run(["xdg-open", path])
            else:
                messagebox.showerror("Ошибка", "Файл не найден")

        ctk.CTkButton(win, text="Открыть файл", command=open_file, fg_color=ACCENT, hover_color=ACCENT_HOVER).pack(pady=12)

    def open_file_from_catalog(self):
        """Горячая клавиша Ctrl+O: открыть файл выделенной записи."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Предупреждение", "Выберите запись")
            return
        photo_id = int(self.tree.item(selected[0], "values")[0])
        photo = self.db.get_photo_by_id(photo_id, self.user["id"])
        if photo:
            path = photo["file_path"]
            if os.path.exists(path):
                if os.name == 'nt':
                    os.startfile(path)
                else:
                    subprocess.run(["xdg-open", path])
            else:
                messagebox.showerror("Ошибка", "Файл не найден")

    def build_tags_tab(self):
        frame = self.tab_tags
        tags_card = ctk.CTkFrame(frame, fg_color="#0F172A")
        tags_card.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.tags_listbox = tk.Listbox(
            tags_card,
            font=FONT_FAMILY,
            bg="#0F172A",
            fg="#E2E8F0",
            selectbackground="#1D4ED8",
            relief=tk.FLAT,
            highlightthickness=0,
        )
        self.tags_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def refresh_tags(self):
        self.tags_listbox.delete(0, tk.END)
        tags = self.db.get_all_unique_tags(self.user["id"])
        for tag in tags:
            self.tags_listbox.insert(tk.END, tag)

    def search_by_tag(self):
        tag = simpledialog.askstring("Поиск по тегу", "Введите тег для поиска:")
        if tag:
            self.current_tag_filter = tag.strip()
            self.current_start_date = None
            self.current_end_date = None
            self.refresh_catalog()

    def search_by_date(self):
        start = simpledialog.askstring("Поиск по дате", "Начальная дата (ГГГГ-ММ-ДД):")
        end = simpledialog.askstring("Поиск по дате", "Конечная дата (ГГГГ-ММ-ДД):")
        if start and end:
            try:
                datetime.strptime(start, "%Y-%m-%d")
                datetime.strptime(end, "%Y-%m-%d")
                self.current_start_date = start
                self.current_end_date = end
                self.current_tag_filter = None
                self.refresh_catalog()
            except ValueError:
                messagebox.showerror("Ошибка", "Неверный формат даты")

    def reset_filters(self):
        self.current_tag_filter = None
        self.current_start_date = None
        self.current_end_date = None
        self.refresh_catalog()

    def export_csv(self):
        photos = self.db.get_photos(
            self.user["id"],
            tag_filter=self.current_tag_filter,
            start_date=self.current_start_date,
            end_date=self.current_end_date
        )
        if not photos:
            messagebox.showinfo("Информация", "Нет данных для экспорта")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV файлы", "*.csv")])
        if file_path:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["ID", "Название", "Описание", "Дата", "Путь", "Теги", "Категория"])
                for p in photos:
                    writer.writerow([p["id"], p["title"], p["description"], p["date_taken"], p["file_path"], p["tags"], p["category"]])
            messagebox.showinfo("Успех", f"Экспорт завершён: {file_path}")

    def new_record(self):
        self.notebook.set("Добавить фото")
        self.title_entry.focus()

    def about(self):
        messagebox.showinfo("О программе", "Коллекция фотографий\nВерсия 1.0\nРазработано для курсового проекта")

if __name__ == "__main__":
    db = Database()
    root = ctk.CTk()
    LoginApp(root, db)
    root.mainloop()