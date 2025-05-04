from PySide6.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QWidget,
    QTextEdit,
)
from mlconjug3 import Conjugator  # Importer mlconjug3 pour la conjugaison


class ConjugatorApp(QMainWindow):
    def __init__(self, font_size):
        super().__init__()
        self.setWindowTitle("Conjugateur Français")
        self.font_size = font_size
        self.conjugator = Conjugator()
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        layout = QVBoxLayout()

        # Champ de saisie pour le mot
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("Entrez un mot...")
        layout.addWidget(self.word_input)

        # Filtre pour le temps littéraire
        self.tense_filter = QComboBox()
        self.tense_filter.addItems(
            ["Tous les temps", "Passé simple", "Imparfait du subjonctif"]
        )
        layout.addWidget(self.tense_filter)

        # Bouton pour rechercher
        search_button = QPushButton("Rechercher")
        search_button.clicked.connect(self.search_conjugations)
        layout.addWidget(search_button)

        # Zone de texte pour afficher les résultats
        self.results_display = QTextEdit()
        self.results_display.setReadOnly(True)
        layout.addWidget(self.results_display)

        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        self.setStyleSheet(f"* {{ font-size: {self.font_size}px; }}")

    def search_conjugations(self):
        """Recherche les conjugaisons pour le mot donné et applique le filtre."""
        word = self.word_input.text().strip()
        tense = self.tense_filter.currentText()

        if not word:
            self.results_display.setText("Veuillez entrer un mot.")
            return

        try:
            conjugations = self.conjugator.conjugate(word)
            results = []

            for mode, tenses in conjugations.items():
                for tense_name, forms in tenses.items():
                    if tense == "Tous les temps" or tense_name == tense:
                        results.append(f"{mode} - {tense_name}:\n" + "\n".join(forms))

            if results:
                self.results_display.setText("\n\n".join(results))
            else:
                self.results_display.setText(
                    "Aucune conjugaison trouvée pour ce filtre."
                )
        except Exception as e:
            self.results_display.setText(f"Erreur: {str(e)}")
