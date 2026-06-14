import os
import sqlite3
import datetime
import webbrowser
import glob
from pathlib import Path

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.dropdown import DropDown
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.utils import platform, get_color_from_hex
from kivy.clock import Clock
from kivy.graphics import RoundedRectangle, Color

from PIL import Image, ImageDraw, ImageFont

# ================= COULEURS =================
COLOR_BG = get_color_from_hex('#F5F7FA')
COLOR_PRIMARY = get_color_from_hex('#2196F3')
COLOR_SUCCESS = get_color_from_hex('#4CAF50')
COLOR_DANGER = get_color_from_hex('#F44336')
COLOR_WARNING = get_color_from_hex('#FF9800')
COLOR_TEXT = get_color_from_hex("#787676")
COLOR_SECONDARY_TEXT = get_color_from_hex("#AC9A9A")
COLOR_CARD = get_color_from_hex("#FFFFFF")

BUTTON_HEIGHT = dp(40)
TEXT_INPUT_HEIGHT = dp(40)
FONT_SIZE_NORMAL = dp(16)
FONT_SIZE_LARGE = dp(18)
SPACING = dp(8)
PADDING = dp(10)

# ================= STOCKAGE (FIXE) =================
STORAGE_PATH = None
DB_PATH = None

def get_storage_path():
    """Dossier fixe : d'abord /storage/emulated/0/magaplant, sinon Documents/magaplant"""
    if platform == 'android':
        # Essai du dossier racine
        root_path = "/storage/emulated/0/magaplant"
        try:
            os.makedirs(root_path, exist_ok=True)
            # Test écriture
            test_file = os.path.join(root_path, ".write_test")
            with open(test_file, 'w') as f:
                f.write("ok")
            os.remove(test_file)
            print(f"[STORAGE] Utilisation de : {root_path}")
            return root_path
        except:
            # Fallback vers Documents
            from jnius import autoclass
            Environment = autoclass('android.os.Environment')
            docs_dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOCUMENTS)
            path = os.path.join(docs_dir.getAbsolutePath(), "magaplant")
            os.makedirs(path, exist_ok=True)
            print(f"[STORAGE] Fallback vers : {path}")
            return path
    elif platform == 'ios':
        path = os.path.expanduser('~/Documents/magaplant')
        os.makedirs(path, exist_ok=True)
        return path
    else:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        os.makedirs(path, exist_ok=True)
        return path

def init_storage():
    global STORAGE_PATH, DB_PATH
    STORAGE_PATH = get_storage_path()
    DB_PATH = os.path.join(STORAGE_PATH, "gestion_pro.db")
    init_db()
    print(f"[INFO] Base de données : {DB_PATH}")

# ================= BASE DE DONNÉES =================
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS factures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_nom TEXT,
                date TEXT,
                total_brut REAL,
                remise_pourcent REAL,
                total_net REAL,
                fichier_image TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS details_facture (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                facture_id INTEGER,
                article TEXT,
                qte INTEGER,
                prix REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT UNIQUE
            )
        """)
        conn.commit()

def get_all_articles():
    if DB_PATH is None or not os.path.exists(DB_PATH):
        return []
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT nom FROM articles ORDER BY nom")
        return [row[0] for row in cursor.fetchall()]

def add_article_if_new(nom):
    if not nom or not nom.strip() or DB_PATH is None:
        return False
    with sqlite3.connect(DB_PATH) as conn:
        try:
            conn.execute("INSERT INTO articles (nom) VALUES (?)", (nom.strip(),))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

# ================= GÉNÉRATION IMAGE MULTIPAGES =================
def generer_image_multipage(nom, transactions, t_brut, t_remise_pourcent, t_net):
    print(f"[DEBUG] Génération image pour {nom}")
    print(f"[DEBUG] Dossier : {STORAGE_PATH}")
    safe_nom = nom.replace(" ", "_").replace("/", "_")
    date_str = datetime.date.today().strftime("%Y%m%d")
    
    width, height = 800, 1100
    marge_haut = 180
    marge_bas = 80
    hauteur_dispo = height - marge_haut - marge_bas
    hauteur_ligne = 24
    max_articles_par_page = max(1, hauteur_dispo // hauteur_ligne)
    
    try:
        font_title = ImageFont.truetype("arial.ttf", 24)
        font_normal = ImageFont.truetype("arial.ttf", 16)
        font_bold = ImageFont.truetype("arialbd.ttf", 16)
        font_small = ImageFont.truetype("arial.ttf", 12)
    except:
        font_title = ImageFont.load_default()
        font_normal = ImageFont.load_default()
        font_bold = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Découpage en pages
    pages = []
    for i in range(0, len(transactions), max_articles_par_page):
        pages.append(transactions[i:i+max_articles_par_page])
    
    # Largeurs approximatives des colonnes (pour alignement à droite)
    col_widths = [500, 60, 80, 90]  # Article, Qté, Prix, Total
    col_x = [50, 450, 550, 650]      # Positions x de début de chaque colonne
    
    filenames = []
    for page_idx, page_trans in enumerate(pages, start=1):
        if len(pages) > 1:
            filename = os.path.join(STORAGE_PATH, f"{safe_nom}_{date_str}_page{page_idx}.png")
        else:
            filename = os.path.join(STORAGE_PATH, f"{safe_nom}_{date_str}.png")
        filenames.append(filename)
        
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        y = 0
        
        # En-tête
        y = 30
        draw.text((width//2, y), "MAGAPLANT", fill='black', font=font_title, anchor='mt')
        y += 40
        draw.text((width//2, y), "TEL / WhatsApp : 06 66 14 46 36", fill='black', font=font_small, anchor='mt')
        y += 20
        draw.text((width//2, y), "Email : magaplant.azrou@gmail.com", fill='black', font=font_small, anchor='mt')
        y += 30
        draw.line((50, y, width-50, y), fill='black', width=2)
        y += 15
        
        # Client
        draw.text((50, y), f"Date : {datetime.date.today()}", fill='black', font=font_normal)
        y += 10
        draw.text((width//2, y), f"Client : {nom}", fill='black', font=font_bold)
        y += 50
        
        # Tableau header
        draw.text((col_x[0], y), "Article", fill='black', font=font_bold)
        draw.text((col_x[1], y), "        Qté", fill='black', font=font_bold)
        draw.text((col_x[2], y), "          Prix", fill='black', font=font_bold)
        draw.text((col_x[3], y), "          Total", fill='black', font=font_bold)
        y += 20
        draw.line((50, y, width-50, y), fill='black', width=1)
        y += 10
        
        # Articles de la page
        for t in page_trans:
            total = t["qte"] * t["prix"]
            
            # Article : aligné à gauche (inchangé)
            draw.text((col_x[0], y), t['article'][:30], fill='black', font=font_normal)
            
            # Qté : aligné à droite
            qte_text = str(t['qte'])
            bbox = draw.textbbox((0, 0), qte_text, font=font_normal)
            text_width = bbox[2] - bbox[0]
            draw.text((col_x[1] + col_widths[1] - text_width, y), qte_text, fill='black', font=font_normal)
            
            # Prix : aligné à droite
            prix_text = f"{t['prix']:.2f}"
            bbox = draw.textbbox((0, 0), prix_text, font=font_normal)
            text_width = bbox[2] - bbox[0]
            draw.text((col_x[2] + col_widths[2] - text_width, y), prix_text, fill='black', font=font_normal)
            
            # Total : aligné à droite
            total_text = f"{total:.2f}"
            bbox = draw.textbbox((0, 0), total_text, font=font_normal)
            text_width = bbox[2] - bbox[0]
            draw.text((col_x[3] + col_widths[3] - text_width, y), total_text, fill='black', font=font_normal)
            
            y += hauteur_ligne
        
        # Pied de page (totaux seulement sur la dernière)
        if page_idx == len(pages):
            y += 10
            draw.line((50, y, width-50, y), fill='black', width=1)
            y += 15
            
            # Alignement à droite pour les totaux
            
            if t_remise_pourcent > 0:
                remise_amount = t_brut * (t_remise_pourcent / 100)

                brut_text = f"Total Brut : {t_brut:.2f} DH"
                bbox = draw.textbbox((0, 0), brut_text, font=font_normal)
                text_width = bbox[2] - bbox[0]
                draw.text((width - 20 - text_width, y), brut_text, fill='black', font=font_normal)
                y += 25

                remise_text = f"Remise ({int(t_remise_pourcent)}%) : -{remise_amount:.2f} DH"
                bbox = draw.textbbox((0, 0), remise_text, font=font_normal)
                text_width = bbox[2] - bbox[0]
                draw.text((width - 20 - text_width, y), remise_text, fill='red', font=font_normal)
                y += 25
            
            net_text = f"NET A PAYER : {t_net:.2f} DH"
            bbox = draw.textbbox((0, 0), net_text, font=font_bold)
            text_width = bbox[2] - bbox[0]
            draw.text((width - 20 - text_width, y), net_text, fill='green', font=font_bold)
        
        # Bas de page
        draw.text((width//2, height-40), "Merci pour votre confiance", fill='black', font=font_small, anchor='mt')
        draw.text((width-50, height-20), f"Page {page_idx}/{len(pages)}", fill='black', font=font_small, anchor='rb')
        draw.line((50, height-50, width-50, height-50), fill='black', width=1)
        
        img.save(filename)
        print(f"[DEBUG] Fichier créé : {filename}")
    
    if filenames and os.path.exists(filenames[0]):
        print(f"[DEBUG] Taille du fichier : {os.path.getsize(filenames[0])} octets")
        return filenames[0]
    else:
        print(f"[ERREUR] Aucun fichier généré !")
        return None

# ================= COMPOSANTS UI (inchangés) =================
class StyledButton(Button):
    def __init__(self, **kwargs):
        bg_color = kwargs.pop('background_color', COLOR_PRIMARY)
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0,0,0,0)
        self.color = get_color_from_hex("#594646")
        self.border = (0,0,0,0)
        self.size_hint_y = None
        self.height = BUTTON_HEIGHT
        self.font_size = FONT_SIZE_NORMAL
        self.bg_color = bg_color
        self.bind(pos=self.update_round_corners, size=self.update_round_corners)
        self.update_round_corners()

    def update_round_corners(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])

class SearchableSpinner(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.multiline = False
        self.size_hint_y = None
        self.height = TEXT_INPUT_HEIGHT
        self.font_size = FONT_SIZE_NORMAL
        self.background_color = (1,1,1,1)
        self.foreground_color = COLOR_TEXT
        self.padding = (dp(10), dp(12))
        self.hint_text = "Article"
        self.bind(focus=self.on_focus)
        self.bind(text=self.on_text_change)
        self.dropdown = None
        self.all_items = []
        self.filtered_items = []
        Clock.schedule_once(lambda dt: self.load_articles(), 0.5)

    def load_articles(self):
        if DB_PATH and os.path.exists(DB_PATH):
            self.all_items = get_all_articles()
        else:
            self.all_items = []
        self.filtered_items = self.all_items[:]

    def on_focus(self, instance, value):
        if value:
            self.load_articles()
            self.show_dropdown()
        else:
            self.hide_dropdown()

    def on_text_change(self, instance, value):
        if self.focus and self.dropdown and self.dropdown.attach_to:
            text_lower = value.strip().lower()
            if text_lower:
                self.filtered_items = [item for item in self.all_items if text_lower in item.lower()]
            else:
                self.filtered_items = self.all_items[:]
            self.update_dropdown_items()

    def show_dropdown(self):
        if self.dropdown:
            return
        self.dropdown = DropDown()
        self.dropdown.auto_width = False
        self.dropdown.width = self.width
        self.update_dropdown_items()
        self.dropdown.open(self)

    def update_dropdown_items(self):
        if not self.dropdown:
            return
        self.dropdown.clear_widgets()
        for item in self.filtered_items:
            item_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(5))
            btn_select = Button(text=item, size_hint_x=0.8,
                                background_normal='', background_color=(1,1,1,1),
                                color=COLOR_TEXT, font_size=FONT_SIZE_NORMAL)
            btn_select.bind(on_release=lambda btn, i=item: self.select_article(i))
            btn_delete = Button(text="X", size_hint_x=0.2,
                                background_normal='', background_color=COLOR_DANGER,
                                color=get_color_from_hex("#FFFFFF"), font_size=FONT_SIZE_NORMAL)
            btn_delete.bind(on_release=lambda btn, i=item: self.confirm_delete_article(i))
            item_layout.add_widget(btn_select)
            item_layout.add_widget(btn_delete)
            self.dropdown.add_widget(item_layout)

    def confirm_delete_article(self, nom):
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM details_facture WHERE article = ?", (nom,))
            count = cursor.fetchone()[0]
        if count > 0:
            self.show_popup("Impossible", f"L'article '{nom}' est utilisé dans {count} facture(s).\nSuppression refusée.")
            return

        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        content.add_widget(Label(text=f"Supprimer l'article '{nom}' ?", color=COLOR_TEXT))
        btn_layout = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        btn_ok = StyledButton(text="Oui", background_color=COLOR_DANGER)
        btn_cancel = StyledButton(text="Non", background_color=COLOR_PRIMARY)
        popup = Popup(title="Confirmation", content=content, size_hint=(0.7, 0.3))
        btn_ok.bind(on_release=lambda x: self.delete_article(nom, popup))
        btn_cancel.bind(on_release=lambda x: popup.dismiss())
        btn_layout.add_widget(btn_ok)
        btn_layout.add_widget(btn_cancel)
        content.add_widget(btn_layout)
        popup.open()

    def delete_article(self, nom, popup):
        popup.dismiss()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM articles WHERE nom = ?", (nom,))
            conn.commit()
        self.load_articles()
        self.filtered_items = self.all_items[:]
        self.update_dropdown_items()
        app = App.get_running_app()
        if app.root.has_screen('articles'):
            app.root.get_screen('articles').refresh_articles()
        self.show_popup("Succès", f"Article '{nom}' supprimé")

    def show_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message, color=COLOR_TEXT, font_size=FONT_SIZE_NORMAL),
                      size_hint=(0.8, 0.4))
        popup.open()

    def select_article(self, item):
        self.text = item
        self.hide_dropdown()

    def hide_dropdown(self):
        if self.dropdown:
            self.dropdown.dismiss()
            self.dropdown = None

    def get_article(self):
        return self.text.strip()

# ================= ÉCRAN FACTURE =================
class InvoiceScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.transactions = []
        self.editing_id = None
        self.build_ui()
        self.update_totals()

    def build_ui(self):
        main_layout = BoxLayout(orientation='vertical', padding=PADDING, spacing=SPACING)
        with self.canvas.before:
            Color(*COLOR_BG)
            self.bg_rect = RoundedRectangle(size=self.size, radius=[0])
        self.bind(size=self._update_bg)

        btn_row = BoxLayout(size_hint_y=None, height=BUTTON_HEIGHT, spacing=SPACING)
        self.btn_invoice = StyledButton(text="Facture", bold=True, background_color=COLOR_PRIMARY)
        self.btn_invoice.bind(on_press=self.show_invoice)
        self.btn_history = StyledButton(text="Historique", bold=True, background_color=get_color_from_hex("#748FB8"))
        self.btn_history.bind(on_press=lambda x: App.get_running_app().show_history(x))
        self.btn_validate = StyledButton(text="Valider", bold=True, background_color=COLOR_SUCCESS)
        self.btn_validate.bind(on_press=self.validate_invoice)
        btn_row.add_widget(self.btn_invoice)
        btn_row.add_widget(self.btn_history)
        btn_row.add_widget(self.btn_validate)
        main_layout.add_widget(btn_row)

        client_row = BoxLayout(size_hint_y=None, height=dp(47), spacing=SPACING)
        self.client_name = TextInput(hint_text="Nom client", multiline=False,
                                     background_color=(1,1,1,1), foreground_color=COLOR_TEXT,
                                     padding=(dp(10), dp(12)), font_size=dp(18))
        self.add_trans_btn = StyledButton(text="Ajouter", bold=True, background_color=COLOR_SUCCESS, size_hint_x=0.3)
        self.add_trans_btn.bind(on_press=self.add_transaction)
        client_row.add_widget(self.client_name)
        client_row.add_widget(self.add_trans_btn)
        main_layout.add_widget(client_row)

        article_row = BoxLayout(size_hint_y=None, height=TEXT_INPUT_HEIGHT, spacing=SPACING)
        self.article_input = SearchableSpinner()
        self.qte_input = TextInput(hint_text="Qté", multiline=False, input_filter='int',
                                   background_color=(1,1,1,1), font_size=FONT_SIZE_NORMAL)
        self.prix_input = TextInput(hint_text="Prix", multiline=False, input_filter='float',
                                    background_color=(1,1,1,1), font_size=FONT_SIZE_NORMAL)
        article_row.add_widget(self.article_input)
        article_row.add_widget(self.qte_input)
        article_row.add_widget(self.prix_input)
        main_layout.add_widget(article_row)

        self.items_container = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(4))
        self.items_container.bind(minimum_height=self.items_container.setter('height'))
        scroll_items = ScrollView()
        scroll_items.add_widget(self.items_container)
        main_layout.add_widget(scroll_items)

        totals_box = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(150), spacing=dp(6), padding=dp(8))
        with totals_box.canvas.before:
            Color(*COLOR_CARD)
            self.totals_bg = RoundedRectangle(pos=totals_box.pos, size=totals_box.size, radius=[dp(12)])
        totals_box.bind(pos=self._update_totals_bg, size=self._update_totals_bg)

        self.total_brut_label = Label(text="Total Brut : 0.00 DH", size_hint_y=None, height=dp(20),
                                      color=COLOR_SECONDARY_TEXT, bold=True, font_size=FONT_SIZE_NORMAL)
        self.total_remise_label = Label(text="Remise : 0.00 DH", size_hint_y=None, height=dp(20),
                                        color=COLOR_DANGER, bold=True, font_size=FONT_SIZE_NORMAL)
        self.total_net_label = Label(text="NET A PAYER : 0.00 DH", size_hint_y=None, height=dp(32),
                                     color=COLOR_SUCCESS, font_size=FONT_SIZE_LARGE, bold=True)

        disc_row = BoxLayout(size_hint_y=None, height=TEXT_INPUT_HEIGHT, spacing=SPACING)
        disc_label = Label(text="R", size_hint_x=None, width=dp(70), color=COLOR_TEXT, font_size=FONT_SIZE_NORMAL)
        self.discount_input = TextInput(text="0", multiline=False, input_filter='float',
                                        size_hint_x=None, width=dp(80),
                                        background_color=(1,1,1,1), font_size=dp(18))
        self.discount_input.bind(text=self.on_discount_change)
        reset_btn = StyledButton(text="Vider", bold=True, background_color=COLOR_DANGER)
        reset_btn.bind(on_press=self.reset_form)
        disc_row.add_widget(disc_label)
        disc_row.add_widget(self.discount_input)
        disc_row.add_widget(reset_btn)

        totals_box.add_widget(self.total_brut_label)
        totals_box.add_widget(self.total_remise_label)
        totals_box.add_widget(self.total_net_label)
        totals_box.add_widget(disc_row)
        main_layout.add_widget(totals_box)

        self.add_widget(main_layout)

    def _update_bg(self, instance, value):
        self.bg_rect.size = self.size

    def _update_totals_bg(self, instance, value):
        self.totals_bg.pos = instance.pos
        self.totals_bg.size = instance.size

    def add_transaction(self, instance):
        article = self.article_input.get_article()
        if not article:
            self.show_popup("Erreur", "Veuillez saisir ou sélectionner un article")
            return
        qte_str = self.qte_input.text.strip()
        prix_str = self.prix_input.text.strip()
        if not qte_str or not prix_str:
            self.show_popup("Erreur", "Quantité et prix requis")
            return
        try:
            qte = int(qte_str)
            prix = float(prix_str)
            if qte <= 0 or prix <= 0:
                raise ValueError
        except ValueError:
            self.show_popup("Erreur", "Quantité et prix doivent être des nombres positifs")
            return
        add_article_if_new(article)
        self.article_input.load_articles()
        self.transactions.append({"article": article, "qte": qte, "prix": prix})
        self.article_input.text = ""
        self.qte_input.text = ""
        self.prix_input.text = ""
        self.refresh_items_display()
        Clock.schedule_once(lambda dt: setattr(self.article_input, 'focus', True), 0.1)

    def delete_transaction(self, index):
        if 0 <= index < len(self.transactions):
            del self.transactions[index]
            self.refresh_items_display()

    def refresh_items_display(self):
        self.items_container.clear_widgets()
        for idx, item in enumerate(self.transactions):
            row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(4))
            info = Label(text=f"{item['article']}  ---->  {item['qte']} x {item['prix']:.2f}",
                         size_hint_x=0.6, halign='left', valign='middle', color=COLOR_TEXT,
                         font_size=dp(14))
            info.bind(size=info.setter('text_size'))
            total = Label(text=f"{item['qte'] * item['prix']:.2f}", size_hint_x=0.2,
                         color=COLOR_SUCCESS, bold=True, font_size=dp(14))
            delete_btn = StyledButton(text="X", background_color=COLOR_DANGER, size_hint_x=0.08)
            delete_btn.bind(on_press=lambda btn, i=idx: self.delete_transaction(i))
            row.add_widget(info)
            row.add_widget(total)
            row.add_widget(delete_btn)
            self.items_container.add_widget(row)
        self.update_totals()

    def update_totals(self):
        brut = sum(t["prix"] * t["qte"] for t in self.transactions)
        try:
            remise_pc = float(self.discount_input.text or "0")
        except ValueError:
            remise_pc = 0.0
        remise_dh = brut * (remise_pc / 100)
        net = brut - remise_dh
        self.total_brut_label.text = f"Total Brut : {brut:.2f} DH"
        self.total_remise_label.text = f"Remise ({remise_pc:.0f}%) : -{remise_dh:.2f} DH"
        self.total_net_label.text = f"NET A PAYER : {net:.2f} DH"
        self.total_brut_label.opacity = 1 if remise_pc > 0 else 0
        self.total_remise_label.opacity = 1 if remise_pc > 0 else 0

    def on_discount_change(self, instance, value):
        self.update_totals()

    def reset_form(self, instance=None):
        self.transactions.clear()
        self.client_name.text = ""
        self.article_input.text = ""
        self.qte_input.text = ""
        self.prix_input.text = ""
        self.discount_input.text = "0"
        self.editing_id = None
        self.refresh_items_display()

    def validate_invoice(self, instance):
        if not self.client_name.text.strip():
            self.show_popup("Erreur", "Nom client requis")
            return
        if not self.transactions:
            self.show_popup("Erreur", "Ajoutez au moins un article")
            return
        brut = sum(t["prix"] * t["qte"] for t in self.transactions)
        try:
            remise_pc = float(self.discount_input.text or "0")
        except ValueError:
            remise_pc = 0.0
        net = brut - (brut * (remise_pc / 100))

        # Génération image
        img_path = generer_image_multipage(self.client_name.text, self.transactions, brut, remise_pc, net)
        if not img_path:
            self.show_popup("Erreur", "La génération de l'image a échoué. Vérifiez les permissions.")
            return

        # Enregistrement en base
        with sqlite3.connect(DB_PATH) as conn:
            if self.editing_id:
                # Édition : on supprime l'ancienne image (si différente)
                old_img = conn.execute("SELECT fichier_image FROM factures WHERE id=?", (self.editing_id,)).fetchone()
                if old_img and old_img[0] and os.path.exists(old_img[0]) and old_img[0] != img_path:
                    base_old = old_img[0].rsplit('_page', 1)[0] if '_page' in old_img[0] else old_img[0].replace('.png', '')
                    for f in glob.glob(f"{base_old}*.png"):
                        try:
                            os.remove(f)
                            print(f"[DEBUG] Ancienne image supprimée : {f}")
                        except:
                            pass
                conn.execute("""
                    UPDATE factures
                    SET client_nom=?, date=?, total_brut=?, remise_pourcent=?, total_net=?, fichier_image=?
                    WHERE id=?
                """, (self.client_name.text, str(datetime.date.today()), brut, remise_pc, net, img_path, self.editing_id))
                conn.execute("DELETE FROM details_facture WHERE facture_id=?", (self.editing_id,))
                facture_id = self.editing_id
            else:
                # Nouvelle facture
                cur = conn.execute("""
                    INSERT INTO factures (client_nom, date, total_brut, remise_pourcent, total_net, fichier_image)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (self.client_name.text, str(datetime.date.today()), brut, remise_pc, net, img_path))
                facture_id = cur.lastrowid

            for item in self.transactions:
                conn.execute("INSERT INTO details_facture(facture_id, article, qte, prix) VALUES (?, ?, ?, ?)",
                            (facture_id, item["article"], item["qte"], item["prix"]))
            conn.commit()

        self.reset_form()
        self.show_popup("Succès", f"Facture enregistrée avec succès\n\nFichier : {os.path.basename(img_path)}")

    def show_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message, color=COLOR_TEXT, font_size=FONT_SIZE_NORMAL),
                      size_hint=(0.8, 0.4))
        popup.open()

    def show_invoice(self, instance):
        App.get_running_app().root.current = 'invoice'

# ================= ÉCRAN HISTORIQUE =================
class HistoryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=PADDING, spacing=SPACING)
        with self.canvas.before:
            Color(*COLOR_BG)
            self.bg_rect = RoundedRectangle(size=self.size, radius=[0])
        self.bind(size=self._update_bg)

        btn_row = BoxLayout(size_hint_y=None, height=BUTTON_HEIGHT, spacing=SPACING)
        btn_invoice = StyledButton(text="Facture", bold=True, background_color=COLOR_PRIMARY)
        btn_invoice.bind(on_press=self.go_to_invoice)
        btn_row.add_widget(btn_invoice)
        layout.add_widget(btn_row)

        self.history_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(10))
        self.history_list.bind(minimum_height=self.history_list.setter('height'))
        scroll = ScrollView()
        scroll.add_widget(self.history_list)
        layout.add_widget(scroll)
        self.add_widget(layout)

    def _update_bg(self, instance, value):
        self.bg_rect.size = self.size

    def on_enter(self):
        self.load_history()

    def go_to_invoice(self, instance):
        App.get_running_app().root.current = 'invoice'

    def load_history(self):
        if DB_PATH is None or not os.path.exists(DB_PATH):
            return
        self.history_list.clear_widgets()
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute("SELECT id, client_nom, date, total_net, fichier_image FROM factures ORDER BY id DESC")
            for row in cursor:
                card = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60),
                                 padding=dp(5), spacing=dp(5))
                with card.canvas.before:
                    Color(*COLOR_CARD)
                    card.bg_rect = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(12)])
                card.bind(pos=self._update_card_bg, size=self._update_card_bg)

                info = Label(text=f"{row[1]}\n{row[2]}", size_hint_x=0.4, halign='left', valign='middle',
                             color=COLOR_TEXT, font_size=FONT_SIZE_NORMAL)
                info.bind(size=info.setter('text_size'))
                total = Label(text=f"{row[3]:.2f}", size_hint_x=0.2, color=COLOR_SUCCESS, bold=True,
                              font_size=FONT_SIZE_NORMAL)
                btn_edit = StyledButton(text="Mod", background_color=COLOR_PRIMARY, size_hint_x=0.1)
                btn_edit.bind(on_press=lambda btn, fid=row[0]: self.edit_invoice(fid))
                btn_img = StyledButton(text="IMG", background_color=COLOR_WARNING, size_hint_x=0.1)
                btn_img.bind(on_press=lambda btn, path=row[4]: self.open_image(path))
                btn_delete = StyledButton(text="X", background_color=COLOR_DANGER, size_hint_x=0.08)
                btn_delete.bind(on_press=lambda btn, fid=row[0], path=row[4]: self.confirm_delete(fid, path))

                card.add_widget(info)
                card.add_widget(total)
                card.add_widget(btn_edit)
                card.add_widget(btn_img)
                card.add_widget(btn_delete)
                self.history_list.add_widget(card)

    def _update_card_bg(self, instance, value):
        if hasattr(instance, 'bg_rect'):
            instance.bg_rect.pos = instance.pos
            instance.bg_rect.size = instance.size

    def confirm_delete(self, facture_id, img_path):
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
        content.add_widget(Label(text="Supprimer définitivement cette facture ?", color=COLOR_TEXT, font_size=dp(14)))
        btn_layout = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        btn_ok = StyledButton(text="Oui", background_color=COLOR_DANGER)
        btn_cancel = StyledButton(text="Non", background_color=COLOR_PRIMARY)
        popup = Popup(title="Confirmation", content=content, size_hint=(0.7, 0.3))
        btn_ok.bind(on_release=lambda x: self.delete_invoice(facture_id, img_path, popup))
        btn_cancel.bind(on_release=lambda x: popup.dismiss())
        btn_layout.add_widget(btn_ok)
        btn_layout.add_widget(btn_cancel)
        content.add_widget(btn_layout)
        popup.open()

    def delete_invoice(self, facture_id, img_path, popup=None):
        if popup:
            popup.dismiss()
        if img_path:
            base_name = img_path.rsplit('_page', 1)[0] if '_page' in img_path else img_path.replace('.png', '')
            for f in glob.glob(f"{base_name}*.png"):
                try:
                    os.remove(f)
                    print(f"[DEBUG] Image supprimée : {f}")
                except:
                    pass
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM factures WHERE id=?", (facture_id,))
            conn.execute("DELETE FROM details_facture WHERE facture_id=?", (facture_id,))
            conn.commit()
        self.load_history()
        self.show_popup("Supprimé", "Facture supprimée.")

    def edit_invoice(self, facture_id):
        with sqlite3.connect(DB_PATH) as conn:
            facture = conn.execute("SELECT client_nom, remise_pourcent FROM factures WHERE id=?", (facture_id,)).fetchone()
            details = conn.execute("SELECT article, qte, prix FROM details_facture WHERE facture_id=?", (facture_id,)).fetchall()
        if not facture:
            return
        invoice_screen = App.get_running_app().root.get_screen('invoice')
        invoice_screen.reset_form()
        invoice_screen.client_name.text = facture[0]
        invoice_screen.transactions = [{"article": d[0], "qte": d[1], "prix": d[2]} for d in details]
        remise_val = facture[1] if facture[1] is not None else 0.0
        invoice_screen.discount_input.text = f"{remise_val:.2f}".rstrip('0').rstrip('.') if remise_val != 0 else "0"
        invoice_screen.editing_id = facture_id
        invoice_screen.refresh_items_display()
        App.get_running_app().root.current = 'invoice'

    def open_image(self, path):
        print(f"[DEBUG] Tentative ouverture : {path}")
        if not path:
            self.show_popup("Erreur", "Chemin de l'image vide.")
            return
        if not os.path.exists(path):
            self.show_popup("Erreur", f"Fichier introuvable :\n{path}\n\nDossier actuel :\n{STORAGE_PATH}")
            return
        try:
            if platform == 'android':
                from jnius import autoclass
                Intent = autoclass('android.content.Intent')
                Uri = autoclass('android.net.Uri')
                File = autoclass('java.io.File')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                activity = PythonActivity.mActivity
                file = File(path)
                uri = Uri.from_file(file)
                intent = Intent(Intent.ACTION_VIEW)
                intent.setDataAndType(uri, "image/png")
                intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                activity.startActivity(intent)
            else:
                webbrowser.open(f'file://{os.path.abspath(path)}')
        except Exception as e:
            self.show_popup("Info", f"Impossible d'ouvrir l'image.\nErreur : {str(e)}")

    def show_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message, color=COLOR_TEXT, font_size=FONT_SIZE_NORMAL),
                      size_hint=(0.8, 0.4))
        popup.open()

# ================= APPLICATION PRINCIPALE =================
class MagaplantApp(App):
    def build(self):
        try:
            init_storage()
        except Exception as e:
            print(f"Erreur critique stockage : {e}")
        if platform in ('win', 'linux', 'macosx'):
            Window.size = (420, 900)
        else:
            Window.fullscreen = 'auto'
        Window.clearcolor = COLOR_BG
        self.title = "MAGAPLANT"
        sm = ScreenManager()
        sm.add_widget(InvoiceScreen(name='invoice'))
        sm.add_widget(HistoryScreen(name='history'))
        return sm

    def on_start(self):
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE
            ])

        if self.root.current == 'history':
            self.root.get_screen('history').load_history()
        invoice_screen = self.root.get_screen('invoice')
        if hasattr(invoice_screen, 'article_input'):
            invoice_screen.article_input.load_articles()

    def show_history(self, instance):
        self.root.current = 'history'

if __name__ == '__main__':
    MagaplantApp().run()