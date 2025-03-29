import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
from bs4 import BeautifulSoup
import threading
import csv
import os
import re
import json
import time
from urllib.parse import urljoin, urlparse

class EnhancedTGStatParser:
    def __init__(self, root):
        self.root = root
        self.root.title("TGStat Parser - Расширенная версия")
        self.root.geometry("900x700")
        
        # Создаем интерфейс
        self.create_widgets()
        
        # Список для хранения результатов
        self.links = []
        
        # Сессия для запросов
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Referer': 'https://tgstat.ru/',
        })
        
        # Флаг для остановки парсинга
        self.stop_parsing = False
    
    def create_widgets(self):
        # Верхняя панель для ввода URL
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)
        
        # Поле для ввода URL
        ttk.Label(top_frame, text="URL канала:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        # Создаем переменную для хранения URL
        self.url_var = tk.StringVar()
        self.url_var.set("https://tgstat.ru/courses")
        
        # Создаем поле ввода, связанное с переменной
        self.url_entry = ttk.Entry(top_frame, textvariable=self.url_var, width=50)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        
        # Кнопка для запуска парсинга
        self.parse_button = ttk.Button(top_frame, text="Начать парсинг", command=self.start_parsing)
        self.parse_button.grid(row=0, column=2, padx=5, pady=5)
        
        # Кнопка для остановки парсинга
        self.stop_button = ttk.Button(top_frame, text="Остановить", command=self.stop_parsing_process)
        self.stop_button.grid(row=0, column=3, padx=5, pady=5)
        self.stop_button.config(state=tk.DISABLED)
        
        # Кнопка для сохранения результатов
        self.save_button = ttk.Button(top_frame, text="Сохранить в CSV", command=self.save_to_csv)
        self.save_button.grid(row=0, column=4, padx=5, pady=5)
        self.save_button.config(state=tk.DISABLED)
        
        # Настраиваем растяжение колонок
        top_frame.columnconfigure(1, weight=1)
        
        # Опции парсинга
        options_frame = ttk.LabelFrame(self.root, text="Опции парсинга", padding=10)
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Опция для поиска всех ссылок
        self.all_links_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Искать все ссылки на странице",
                        variable=self.all_links_var).grid(row=0, column=0, sticky=tk.W)
        
        # Опция для пагинации
        self.pagination_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Обрабатывать пагинацию",
                        variable=self.pagination_var).grid(row=0, column=1, sticky=tk.W)
        
        # Опция для API запросов
        self.use_api_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Использовать API запросы",
                        variable=self.use_api_var).grid(row=0, column=2, sticky=tk.W)
        
        # Максимальное количество страниц
        ttk.Label(options_frame, text="Макс. страниц:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.max_pages_var = tk.StringVar(value="50")
        ttk.Entry(options_frame, textvariable=self.max_pages_var, width=5).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Задержка между запросами
        ttk.Label(options_frame, text="Задержка (сек):").grid(row=1, column=2, sticky=tk.W, pady=5)
        self.delay_var = tk.StringVar(value="1")
        ttk.Entry(options_frame, textvariable=self.delay_var, width=5).grid(row=1, column=3, sticky=tk.W, pady=5)
        
        # Текстовое поле для вывода результатов
        result_frame = ttk.LabelFrame(self.root, text="Результаты парсинга", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Создаем текстовое поле с прокруткой
        self.result_text = scrolledtext.ScrolledText(result_frame, wrap=tk.WORD)
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        # Статус бар
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Прогресс бар
        self.progress = ttk.Progressbar(status_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=5)
        
        # Статус текст
        self.status_var = tk.StringVar()
        self.status_var.set("Готов к работе")
        status_bar = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.RIGHT, fill=tk.X, padx=10, pady=5)
    
    def start_parsing(self):
        # Получаем URL из переменной
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Ошибка", "Введите URL для парсинга")
            return
        
        # Очищаем результаты
        self.result_text.delete(1.0, tk.END)
        self.links = []
        self.stop_parsing = False
        
        # Блокируем/разблокируем кнопки
        self.parse_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.save_button.config(state=tk.DISABLED)
        
        # Обновляем статус
        self.status_var.set("Парсинг...")
        self.result_text.insert(tk.END, f"Начинаем парсинг URL: {url}\n\n")
        
        # Запускаем парсинг в отдельном потоке
        threading.Thread(target=self.parse_url, args=(url,), daemon=True).start()
    
    def stop_parsing_process(self):
        self.stop_parsing = True
        self.status_var.set("Остановка парсинга...")
        self.result_text.insert(tk.END, "Остановка парсинга...\n")
    
    def parse_url(self, url):
        try:
            # Проверяем URL
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Определяем тип страницы
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Получаем максимальное количество страниц и задержку
            try:
                max_pages = int(self.max_pages_var.get())
                delay = float(self.delay_var.get())
            except ValueError:
                max_pages = 50
                delay = 1
                self.root.after(0, lambda: self.update_status("Ошибка в параметрах, используем значения по умолчанию"))
            
            # Начинаем с первой страницы
            current_page = 1
            total_links = 0
            
            # Если включена опция API запросов, пробуем использовать API
            if self.use_api_var.get() and "courses" in url:
                self.root.after(0, lambda: self.update_status("Используем API для получения данных..."))
                
                # Пытаемся получить данные через API
                api_success = self.parse_via_api(url, max_pages, delay)
                
                if api_success:
                    return
                else:
                    self.root.after(0, lambda: self.update_status("API не сработал, переключаемся на обычный парсинг..."))
            
            # Обычный парсинг с пагинацией
            while current_page <= max_pages and not self.stop_parsing:
                # Формируем URL с пагинацией
                page_url = url
                if current_page > 1 and self.pagination_var.get():
                    # Проверяем формат URL для пагинации
                    if "?" in url:
                        page_url = f"{url}&page={current_page}"
                    else:
                        page_url = f"{url}?page={current_page}"
                
                self.root.after(0, lambda: self.update_status(f"Обработка страницы {current_page}..."))
                self.root.after(0, lambda: self.progress.config(value=(current_page / max_pages * 100)))
                
                # Делаем запрос
                response = self.session.get(page_url, timeout=30)
                response.raise_for_status()
                
                # Сохраняем HTML для отладки (только первую страницу)
                if current_page == 1:
                    with open("debug_response.html", "w", encoding="utf-8") as f:
                        f.write(response.text)
                    self.root.after(0, lambda: self.update_status("HTML сохранен в файл debug_response.html для отладки"))
                
                # Парсим HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Ищем ссылки на Telegram каналы
                new_links = self.extract_links_from_soup(soup, base_url)
                
                # Если не нашли ссылок и это не первая страница, возможно пагинация закончилась
                if not new_links and current_page > 1:
                    self.root.after(0, lambda: self.update_status(f"Страница {current_page} не содержит новых ссылок. Завершаем парсинг."))
                    break
                
                # Добавляем новые ссылки к общему списку
                self.links.extend(new_links)
                total_links += len(new_links)
                
                # Обновляем статус
                self.root.after(0, lambda: self.update_status(f"Найдено {total_links} ссылок (страница {current_page})"))
                
                # Если не включена пагинация, выходим после первой страницы
                if not self.pagination_var.get():
                    break
                
                # Переходим к следующей странице
                current_page += 1
                
                # Задержка между запросами
                if current_page <= max_pages and not self.stop_parsing:
                    time.sleep(delay)
            
            # Обновляем UI в главном потоке
            self.root.after(0, self.update_results)
            
        except Exception as e:
            # Обрабатываем ошибки
            import traceback
            error_details = traceback.format_exc()
            self.root.after(0, lambda: self.show_error(f"{str(e)}\n\nПодробности:\n{error_details}"))
    
    def parse_via_api(self, url, max_pages, delay):
        try:
            # Определяем категорию из URL
            category = url.split('/')[-1]
            
            # Формируем API URL
            api_url = f"https://tgstat.ru/channels/list/{category}"
            
            total_links = 0
            current_page = 1
            
            while current_page <= max_pages and not self.stop_parsing:
                self.root.after(0, lambda: self.update_status(f"API запрос: страница {current_page}..."))
                self.root.after(0, lambda: self.progress.config(value=(current_page / max_pages * 100)))
                
                # Формируем параметры запроса
                params = {
                    'page': current_page,
                    'sort': 'members',
                    'extended': 1
                }
                
                # Делаем API запрос
                response = self.session.get(api_url, params=params, timeout=30)
                
                # Проверяем успешность запроса
                                # Проверяем успешность запроса
                if response.status_code != 200:
                    self.root.after(0, lambda: self.update_status(f"API вернул ошибку: {response.status_code}"))
                    return False
                
                # Пробуем распарсить JSON
                try:
                    data = response.json()
                except:
                    self.root.after(0, lambda: self.update_status("Не удалось распарсить JSON ответ от API"))
                    return False
                
                # Проверяем структуру ответа
                if 'items' not in data:
                    self.root.after(0, lambda: self.update_status("API вернул неожиданный формат данных"))
                    return False
                
                # Извлекаем ссылки на каналы
                new_links = []
                for item in data['items']:
                    if 'username' in item and item['username']:
                        username = item['username']
                        title = item.get('title', username)
                        members = item.get('members', 0)
                        
                        new_links.append({
                            'url': f"https://t.me/{username}",
                            'text': title,
                            'members': members
                        })
                
                # Если не нашли ссылок и это не первая страница, возможно пагинация закончилась
                if not new_links and current_page > 1:
                    self.root.after(0, lambda: self.update_status(f"API: страница {current_page} не содержит новых каналов. Завершаем."))
                    break
                
                # Добавляем новые ссылки к общему списку
                self.links.extend(new_links)
                total_links += len(new_links)
                
                # Обновляем статус
                self.root.after(0, lambda: self.update_status(f"API: найдено {total_links} каналов (страница {current_page})"))
                
                # Проверяем, есть ли еще страницы
                if 'pagination' in data and 'has_next' in data['pagination']:
                    if not data['pagination']['has_next']:
                        self.root.after(0, lambda: self.update_status("API: достигнут конец списка"))
                        break
                
                # Переходим к следующей странице
                current_page += 1
                
                # Задержка между запросами
                if current_page <= max_pages and not self.stop_parsing:
                    time.sleep(delay)
            
            # Обновляем UI в главном потоке
            self.root.after(0, self.update_results)
            return True
            
        except Exception as e:
            self.root.after(0, lambda: self.update_status(f"Ошибка при использовании API: {str(e)}"))
            return False
    
    def extract_links_from_soup(self, soup, base_url):
        """Извлекает ссылки на Telegram каналы из HTML"""
        all_links = []
        
        # Ищем карточки каналов
        channel_cards = soup.find_all(class_=["channel-card", "channel-item"])
        
        if channel_cards:
            self.root.after(0, lambda: self.update_status(f"Найдено {len(channel_cards)} карточек каналов"))
            
            for card in channel_cards:
                # Ищем ссылку на канал
                a_tag = card.find('a', href=True)
                if not a_tag:
                    continue
                
                href = a_tag.get('href', '')
                
                # Проверяем, что это ссылка на Telegram канал
                if '/channel/' in href:
                    # Извлекаем имя канала из URL
                    channel_parts = href.split('/')
                    if len(channel_parts) > 1:
                        channel_name = channel_parts[-1]
                        
                        # Формируем прямую ссылку на Telegram
                        tg_url = f"https://t.me/{channel_name}"
                        
                        # Ищем название канала
                        title_elem = card.find(class_=["channel-name", "channel-title"])
                        title = title_elem.get_text(strip=True) if title_elem else channel_name
                        
                        # Ищем количество подписчиков
                        members_elem = card.find(class_=["channel-members", "members"])
                        members = members_elem.get_text(strip=True) if members_elem else "Неизвестно"
                        
                        all_links.append({
                            'url': tg_url,
                            'text': title,
                            'members': members
                        })
        
        # Если не нашли карточки каналов, ищем все ссылки
        if not all_links and self.all_links_var.get():
            # Ищем все ссылки на странице
            a_tags = soup.find_all('a', href=True)
            
            for a in a_tags:
                href = a.get('href', '')
                
                # Проверяем, что это ссылка на Telegram
                if 't.me/' in href or 'telegram.me/' in href:
                    link_text = a.get_text(strip=True)
                    if not link_text:
                        link_text = a.get('title', '') or href
                    
                    all_links.append({
                        'url': href,
                        'text': link_text
                    })
                # Проверяем ссылки на каналы на tgstat
                elif '/channel/' in href:
                    # Формируем полный URL если это относительная ссылка
                    if href.startswith('/'):
                        href = urljoin(base_url, href)
                    
                    # Извлекаем имя канала
                    channel_parts = href.split('/')
                    if len(channel_parts) > 1:
                        channel_name = channel_parts[-1]
                        tg_url = f"https://t.me/{channel_name}"
                        
                        link_text = a.get_text(strip=True)
                        if not link_text:
                            link_text = a.get('title', '') or channel_name
                        
                        all_links.append({
                            'url': tg_url,
                            'text': link_text
                        })
        
        # Ищем ссылки в тексте с помощью регулярных выражений
        if not all_links:
            html_text = str(soup)
            
            # Ищем ссылки вида t.me/... или telegram.me/...
            tg_links_pattern = r'(https?://)?(t\.me|telegram\.me)/([a-zA-Z0-9_]+)'
            tg_links = re.findall(tg_links_pattern, html_text)
            
            for protocol, domain, username in tg_links:
                if not protocol:
                    protocol = "https://"
                
                full_url = f"{protocol}{domain}/{username}"
                
                # Проверяем, нет ли уже такой ссылки
                if not any(link['url'] == full_url for link in all_links):
                    all_links.append({
                        'url': full_url,
                        'text': f"@{username}"
                    })
        
        # Удаляем дубликаты по URL
        unique_links = []
        seen_urls = set()
        
        for link in all_links:
            url = link['url']
            if url not in seen_urls:
                seen_urls.add(url)
                unique_links.append(link)
        
        return unique_links
    
    def update_status(self, message):
        """Обновляет статус и добавляет сообщение в текстовое поле"""
        self.status_var.set(message)
        self.result_text.insert(tk.END, f"{message}\n")
        self.result_text.see(tk.END)  # Прокручиваем к последней строке
    
    def update_results(self):
        # Обновляем текстовое поле с результатами
        self.result_text.delete(1.0, tk.END)
        
        if not self.links:
            self.result_text.insert(tk.END, "Telegram-ссылки не найдены.\n")
            self.result_text.insert(tk.END, "\nПроверьте следующее:\n")
            self.result_text.insert(tk.END, "1. Правильность введенного URL\n")
            self.result_text.insert(tk.END, "2. Наличие Telegram-ссылок на странице\n")
            self.result_text.insert(tk.END, "3. Файл debug_response.html для анализа содержимого страницы\n")
        else:
            self.result_text.insert(tk.END, f"Найдено {len(self.links)} Telegram-каналов:\n\n")
            
            for i, link in enumerate(self.links, 1):
                text = link['text']
                url = link['url']
                members = link.get('members', 'Неизвестно')
                
                self.result_text.insert(tk.END, f"{i}. {text}\n")
                self.result_text.insert(tk.END, f"   URL: {url}\n")
                if members != 'Неизвестно':
                    self.result_text.insert(tk.END, f"   Подписчиков: {members}\n")
                self.result_text.insert(tk.END, "\n")
        
        # Обновляем статус
        self.status_var.set(f"Найдено Telegram-каналов: {len(self.links)}")
        
        # Разблокируем кнопки
        self.parse_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        if self.links:
            self.save_button.config(state=tk.NORMAL)
    
    def show_error(self, error_message):
        # Показываем сообщение об ошибке
        messagebox.showerror("Ошибка при парсинге", error_message)
        self.result_text.insert(tk.END, f"Ошибка: {error_message}\n")
        
        # Обновляем статус и разблокируем кнопки
        self.status_var.set("Ошибка при парсинге")
        self.parse_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
    
    def save_to_csv(self):
        # Сохраняем результаты в CSV
        if not self.links:
            messagebox.showerror("Ошибка", "Нет данных для сохранения")
            return
        
        try:
            filename = "tgstat_links.csv"
            with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                # Определяем поля для CSV
                fieldnames = ['url', 'text']
                if 'members' in self.links[0]:
                    fieldnames.append('members')
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for link in self.links:
                    # Создаем копию словаря только с нужными полями
                    row = {field: link.get(field, '') for field in fieldnames}
                    writer.writerow(row)
            
            # Показываем сообщение об успехе
            full_path = os.path.abspath(filename)
            messagebox.showinfo("Успех", f"Результаты сохранены в файл:\n{full_path}")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить результаты: {e}")

def main():
    root = tk.Tk()
    app = EnhancedTGStatParser(root)
    root.mainloop()

if __name__ == "__main__":
    main()
