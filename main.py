import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QPushButton,
    QWidget,
    QSlider,  # Importer QSlider pour ajuster la taille de police
    QLabel,  # Importer QLabel pour afficher la taille actuelle
)
from PySide6.QtCore import Qt  # Importer Qt pour l'orientation du slider
from addition import AudioSaverApp  # Importer AudioSaverApp
from retrieval import RetrievalApp  # Importer RetrievalApp
from record_manager import RecordManagerApp  # Importer RecordManagerApp
from additionBulk import BulkAudioSaverApp  # Importer BulkAudioSaverApp
from exporterBulk import BulkAudioExporterApp  # Importer BulkAudioExporterApp
from db import DatabaseManager  # Importer DatabaseManager
from conjugator import ConjugatorApp  # Importer ConjugatorApp


class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Application Principale")
        self.db_manager = DatabaseManager("data.db")
        self.font_size = 12  # Taille de police par défaut
        self.setup_ui()
        self.showMaximized()  # Ouvre la fenêtre principale en mode maximisé

    def setup_ui(self):
        central_widget = QWidget()
        layout = QVBoxLayout()

        # Slider pour ajuster la taille de police
        font_slider_label = QLabel(f"Taille de police: {self.font_size}")
        font_slider = QSlider(Qt.Horizontal)
        font_slider.setMinimum(8)
        font_slider.setMaximum(24)
        font_slider.setValue(self.font_size)
        font_slider.valueChanged.connect(
            lambda value: self.adjust_font_size(value, font_slider_label)
        )
        layout.addWidget(font_slider_label)
        layout.addWidget(font_slider)

        # Bouton pour ouvrir la fonctionnalité d'ajout
        add_button = QPushButton("Ajouter un élément")
        add_button.clicked.connect(self.open_addition_window)
        layout.addWidget(add_button)

        # Bouton pour ouvrir la fonctionnalité de récupération
        retrieve_button = QPushButton("Afficher les éléments")
        retrieve_button.clicked.connect(self.open_retrieval_window)
        layout.addWidget(retrieve_button)

        # Bouton pour ouvrir la gestion des enregistrements
        manage_button = QPushButton("Gérer les enregistrements")
        manage_button.clicked.connect(self.open_record_manager_window)
        layout.addWidget(manage_button)

        # Bouton pour ouvrir la fonctionnalité d'importation en masse
        bulk_import_button = QPushButton("Importer en masse")
        bulk_import_button.clicked.connect(self.open_bulk_import_window)
        layout.addWidget(bulk_import_button)

        # Bouton pour ouvrir la fonctionnalité d'exportation en masse
        bulk_export_button = QPushButton("Exporter en masse")
        bulk_export_button.clicked.connect(self.open_bulk_export_window)
        layout.addWidget(bulk_export_button)

        # Bouton pour ouvrir la fenêtre de conjugaison française
        conjugator_button = QPushButton("Conjugateur Français")
        conjugator_button.clicked.connect(self.open_conjugator_window)
        layout.addWidget(conjugator_button)

        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def adjust_font_size(self, value, label):
        """Ajuste la taille de police dans l'application."""
        self.font_size = value
        label.setText(f"Taille de police: {self.font_size}")
        self.setStyleSheet(f"* {{ font-size: {self.font_size}px; }}")

    def open_addition_window(self):
        if not hasattr(self, "addition_window") or self.addition_window is None:
            self.addition_window = AudioSaverApp(
                self.db_manager, self.font_size
            )  # Passer font_size
        self.addition_window.initialize_ui()  # Appelle la méthode pour configurer l'interface utilisateur
        self.addition_window.show()

    def open_retrieval_window(self):
        """Ouvre la fenêtre RetrievalApp."""
        self.retrieval_window = RetrievalApp(
            self.db_manager, self.font_size
        )  # Passer font_size
        self.retrieval_window.show()

    def open_record_manager_window(self):
        # Vérifiez si la fenêtre existe déjà, sinon créez-la
        if (
            not hasattr(self, "record_manager_window")
            or self.record_manager_window is None
        ):
            self.record_manager_window = RecordManagerApp(
                self.db_manager, self.font_size
            )  # Passer font_size
        self.record_manager_window.show()

    def open_bulk_import_window(self):
        if not hasattr(self, "bulk_import_window") or self.bulk_import_window is None:
            self.bulk_import_window = BulkAudioSaverApp(
                self.db_manager, self.font_size
            )  # Passer font_size
        self.bulk_import_window.show()

    def open_bulk_export_window(self):
        if not hasattr(self, "bulk_export_window") or self.bulk_export_window is None:
            self.bulk_export_window = BulkAudioExporterApp(
                self.db_manager, self.font_size
            )  # Passer font_size
        self.bulk_export_window.show()

    def open_conjugator_window(self):
        """Ouvre la fenêtre ConjugatorApp."""
        if not hasattr(self, "conjugator_window") or self.conjugator_window is None:
            self.conjugator_window = ConjugatorApp(self.font_size)  # Passer font_size
        self.conjugator_window.show()

    def closeEvent(self, event):
        """Fermer proprement la base de données et les fenêtres secondaires."""
        if hasattr(self, "db_manager"):
            self.db_manager.close_connection()  # Fermer la base de données
        if hasattr(self, "addition_window") and self.addition_window is not None:
            try:
                if self.addition_window.isVisible():
                    self.addition_window.close()
            except RuntimeError:
                self.addition_window = None  # L'objet a déjà été supprimé
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)

    # Exécute l'application principale
    main_window = MainApp()
    main_window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
