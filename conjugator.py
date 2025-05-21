from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QMessageBox,
    QDialog,
    QGridLayout,
    QLabel,
    QScrollArea,
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
    QTextEdit,
)
from PySide6.QtCore import Qt  # Importer Qt pour le formatage du texte
from PySide6.QtGui import (
    QKeySequence,
    QShortcut,  # Déplacé ici depuis PySide6.QtWidgets
)  # Importer QShortcut pour les raccourcis clavier
from mlconjug3 import Conjugator  # Importer mlconjug3 pour la conjugaison
import toml  # Importer toml pour lire/écrire dans le fichier de configuration


class ResultsDialog(QDialog):
    """Boîte de dialogue personnalisée pour afficher les résultats de conjugaison en colonnes."""

    def __init__(self, title, results, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)

        # Obtenir la taille de l'écran avec la méthode moderne
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(screen.width() * 0.7, screen.height() * 0.7)

        # Créer une zone de défilement pour les résultats
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # Widget conteneur pour les résultats
        results_widget = QWidget()
        layout = QGridLayout(results_widget)

        # Déterminer le nombre optimal de colonnes (dépend de la largeur de l'écran)
        num_results = len(results)
        max_columns = max(1, min(5, num_results))  # Entre 1 et 5 colonnes

        # Calculer le nombre de lignes nécessaires
        rows_per_column = -(-num_results // max_columns)  # Arrondi supérieur

        # Placer les résultats dans le grid layout
        for i, result in enumerate(results):
            col = i // rows_per_column
            row = i % rows_per_column

            label = QLabel()
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setText(result)
            label.setWordWrap(True)

            layout.addWidget(label, row, col)

        # Configurer la zone de défilement
        scroll_area.setWidget(results_widget)

        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll_area)

        self.setLayout(main_layout)


class ConjugatorApp(QMainWindow):
    def __init__(self, font_size):
        super().__init__()
        self.setWindowTitle("Conjugateur Français")
        self.font_size = font_size
        self.conjugator = Conjugator()
        self.config_path = "/media/ron/Ronzz_Core/nextCloudSync/mindiverse-life/coucou/coucou/config.toml"
        self.tenses_by_mood = {
            "Infinitif": ["Infinitif Présent"],
            "Indicatif": ["Présent", "Passé Simple", "Imparfait", "Futur"],
            "Conditionnel": ["Présent"],
            "Subjonctif": ["Présent", "Imparfait"],
            "Imperatif": ["Impératif Présent"],
            "Participe": ["Participe Présent", "Participe Passé"],
        }
        self.setup_ui()
        self.load_default_settings()

    def load_default_settings(self):
        """Charge les paramètres par défaut depuis le fichier config.toml."""
        try:
            config = toml.load(self.config_path)
            default_moods = config.get("default_moods", {})
            default_tenses = config.get("default_tenses", {})

            # Appliquer les paramètres par défaut aux cases à cocher des modes
            for checkbox in self.mood_checkboxes:
                checkbox.setChecked(default_moods.get(checkbox.text(), False))

            # Appliquer les paramètres par défaut aux cases à cocher des temps
            for mood, tense, checkbox in self.tense_checkboxes:
                checkbox.setChecked(default_tenses.get(tense, False))
        except Exception as e:
            QMessageBox.warning(
                self,
                "Erreur",
                f"Impossible de charger les paramètres par défaut: {str(e)}",
            )

    def save_default_settings(self):
        """Enregistre les paramètres actuels comme paramètres par défaut dans config.toml."""
        try:
            config = toml.load(self.config_path)

            # Sauvegarder les modes sélectionnés
            config["default_moods"] = {
                checkbox.text(): checkbox.isChecked()
                for checkbox in self.mood_checkboxes
            }

            # Sauvegarder les temps sélectionnés
            config["default_tenses"] = {
                tense: checkbox.isChecked()
                for _, tense, checkbox in self.tense_checkboxes
            }

            with open(self.config_path, "w") as config_file:
                toml.dump(config, config_file)

            QMessageBox.information(
                self, "Succès", "Paramètres enregistrés avec succès."
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Erreur", f"Impossible d'enregistrer les paramètres: {str(e)}"
            )

    def setup_ui(self):
        self.showMaximized()
        central_widget = QWidget()
        layout = QVBoxLayout()

        # Ajout du raccourci clavier pour fermer la fenêtre
        close_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        close_shortcut.activated.connect(self.close)

        # GroupBox pour les moods
        mood_group = QGroupBox("Modes")
        mood_layout = QVBoxLayout()

        self.mood_checkboxes = []
        moods = [
            "Infinitif",
            "Indicatif",
            "Conditionnel",
            "Subjonctif",
            "Imperatif",
            "Participe",
        ]
        for mood in moods:
            checkbox = QCheckBox(mood)
            checkbox.stateChanged.connect(self.update_tense_checkboxes)
            self.mood_checkboxes.append(checkbox)
            mood_layout.addWidget(checkbox)

        mood_group.setLayout(mood_layout)
        layout.addWidget(mood_group)

        # GroupBox pour les temps
        self.tense_group = QGroupBox("Temps")
        self.tense_layout = QVBoxLayout()
        self.tense_checkboxes = []
        self.tense_group.setLayout(self.tense_layout)
        layout.addWidget(self.tense_group)
        # Champ de saisie pour le mot
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("Entrez un mot... (Ctrl+F)")
        layout.addWidget(self.word_input)

        self.word_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.word_shortcut.activated.connect(self.word_input.setFocus)

        # Bouton pour rechercher
        search_button = QPushButton("Rechercher (&S)")
        search_button.clicked.connect(self.search_conjugations)
        layout.addWidget(search_button)

        # Désactiver le bouton si le champ de saisie est vide
        def toggle_button_state():
            search_button.setEnabled(bool(self.word_input.text().strip()))

        self.word_input.textChanged.connect(toggle_button_state)
        toggle_button_state()  # Initialiser l'état du bouton

        # Zone de texte pour afficher les résultats
        self.results_display = QTextEdit()
        self.results_display.setReadOnly(True)
        layout.addWidget(self.results_display)

        # Bouton pour enregistrer les paramètres par défaut
        save_button = QPushButton("Enregistrer les paramètres comme défaut")
        save_button.clicked.connect(self.save_default_settings)
        layout.addWidget(save_button)

        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        self.setStyleSheet(f"* {{ font-size: {self.font_size}px; }}")

    def update_tense_checkboxes(self):
        """Met à jour les options de tense_checkboxes en fonction des moods sélectionnés."""
        selected_moods = [cb.text() for cb in self.mood_checkboxes if cb.isChecked()]

        # Supprimer les widgets existants dans la disposition des tenses
        for i in reversed(range(self.tense_layout.count())):
            widget = self.tense_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        self.tense_checkboxes = []  # Réinitialiser les cases à cocher

        for mood in selected_moods:
            # Ajouter un label pour chaque mood
            mood_label = QGroupBox(mood)
            mood_layout = QVBoxLayout()

            for tense in self.tenses_by_mood.get(mood, []):
                checkbox = QCheckBox(f"{mood} - {tense}")
                checkbox.setChecked(True)  # Cocher la case par défaut
                self.tense_checkboxes.append((mood, tense, checkbox))
                mood_layout.addWidget(checkbox)

            mood_label.setLayout(mood_layout)
            self.tense_layout.addWidget(mood_label)

        self.tense_group.setLayout(self.tense_layout)

    def search_conjugations(self):
        """Recherche les conjugaisons pour le mot donné et applique le filtre."""
        word = self.word_input.text().strip()

        if not word:
            QMessageBox.warning(self, "Erreur", "Veuillez entrer un mot.")
            return

        try:
            verb = self.conjugator.conjugate(word)  # Retourne un objet VerbFr
            # Récupérer les moods et tenses sélectionnés
            selected_mood_tense_pairs = [
                (mood, tense)
                for mood, tense, cb in self.tense_checkboxes
                if cb.isChecked()
            ]

            results = []
            color_map = {
                ("Infinitif", "Infinitif Présent"): "#0000FF",  # Bright blue
                ("Indicatif", "Présent"): "#008000",  # Bright green
                ("Indicatif", "Passé Simple"): "#006400",  # Dark green
                ("Indicatif", "Imparfait"): "#32CD32",  # Lime green
                ("Indicatif", "Futur"): "#008080",  # Teal
                ("Conditionnel", "Présent"): "#FFA500",  # Bright orange
                ("Subjonctif", "Présent"): "#800080",  # Purple
                ("Subjonctif", "Imparfait"): "#9400D3",  # Dark violet
                ("Imperatif", "Impératif Présent"): "#FF0000",  # Bright red
                ("Participe", "Participe Présent"): "#A52A2A",  # Brown
                ("Participe", "Participe Passé"): "#8B4513",  # Saddle brown
            }

            for mood, tense in selected_mood_tense_pairs:
                try:
                    conjugations = verb[(mood, tense)]
                    color = color_map.get(
                        (mood, tense), "black"
                    )  # Couleur par défaut : noir
                    if isinstance(conjugations, dict):
                        formatted_conjugations = "\n".join(
                            [
                                f"  {person} {form}"
                                for person, form in conjugations.items()
                            ]
                        )
                        results.append(
                            f'<span style="color: {color}">'
                            f"{mood} - {tense}:<br>{formatted_conjugations.replace('\n', '<br>')}</span>"
                        )
                    else:
                        results.append(
                            f'<span style="color: {color}">'
                            f"{mood} - {tense}:<br>{conjugations}</span>"
                        )
                except KeyError:
                    results.append(
                        f'<span style="color: {color}">'
                        f"{mood} - {tense}:</span> Non disponible"
                    )

            # Afficher les résultats dans un dialogue multi-colonnes
            dialog = ResultsDialog("Résultats de la conjugaison", results, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur: {str(e)}")
