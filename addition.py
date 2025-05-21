from PySide6.QtWidgets import (
    QFileDialog,
    QMessageBox,
    QPushButton,
    QWidget,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
    QHBoxLayout,
)
from PySide6.QtCore import (
    QThread,
    Signal,
    QObject,
)
from PySide6.QtGui import (
    QKeySequence,
    QShortcut,
)
from common_methods import (
    PlainPasteTextEdit,
    ProgressBarHelper,
    TimeUtils,
)
import os


class ProcessInputsWorker(QObject):
    finished = Signal(bool, str)  # succès, message

    def __init__(
        self,
        db_manager,
        file_path,
        question_data,
        response_data,
        start_time,
        end_time,
        attribution="no-attribution",
    ):
        super().__init__()
        self.db_manager = db_manager
        self.file_path = file_path
        self.question_data = question_data
        self.response_data = response_data
        self.start_time = start_time
        self.end_time = end_time
        self.attribution = attribution

    def run(self):
        try:
            self.db_manager.insert_record(
                self.file_path,
                self.question_data,
                self.response_data,
                self.start_time,
                self.end_time,
                attribution=self.attribution,
            )
            self.finished.emit(True, "Entrée enregistrée avec succès !")
        except Exception as e:
            self.finished.emit(False, f"Échec de l'enregistrement : {e}")


class AudioSaverApp(QWidget):
    def __init__(self, db_manager, font_size=12):  # Ajout de font_size
        super().__init__()
        self.setWindowTitle("Ajouter un élément")
        self.db_manager = db_manager  # Utiliser l'instance partagée de DatabaseManager
        self.font_size = font_size  # Stocker la taille de police
        self.setStyleSheet(
            f"* {{ font-size: {self.font_size}px; }}"
        )  # Appliquer la taille de police
        self.last_audio_path = ""  # Mémorise le dernier chemin audio utilisé
        self.last_attribution = "no-attribution"  # Mémorise la dernière attribution
        # Ajout du raccourci clavier Ctrl+W pour fermer la fenêtre
        close_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        close_shortcut.activated.connect(self.close)

    def initialize_ui(self):
        # Supprimer le layout existant s'il y en a un (pour éviter les doublons et erreurs)
        old_layout = self.layout()
        if old_layout is not None:
            while old_layout.count():
                item = old_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
            QWidget().setLayout(old_layout)  # Détacher le layout de ce widget
        self.setLayout(QVBoxLayout())  # Toujours repartir d'un layout propre
        self.showMaximized()  # Ouvre la fenêtre principale en mode maximisé
        self.upload_audio()

        # Ajouter un bouton pour fermer la fenêtre
        close_button = QPushButton("Fermer (CTRL+W)")
        close_button.clicked.connect(self.close)
        self.layout().addWidget(close_button)

    def closeEvent(self, event):
        """Gérer la fermeture propre de la fenêtre sans supprimer explicitement l'objet C++."""
        super().closeEvent(event)

    def upload_audio(self):
        # Nettoyer le layout existant (pour éviter doublons si réouverture)
        if self.layout() is not None:
            while self.layout().count():
                item = self.layout().takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
        else:
            self.setLayout(QVBoxLayout())

        form_layout = QFormLayout()

        # --- Sélection de fichier média ---
        self.file_path_input = QLineEdit()
        file_button = QPushButton("Sélectionner un fichier média (&A)")
        if self.last_audio_path:
            self.file_path_input.setText(self.last_audio_path)
        file_button.clicked.connect(lambda: self.select_file(self.file_path_input))
        form_layout.addRow("Fichier média (&A) :", file_button)
        form_layout.addRow("", self.file_path_input)

        # --- Saisie des timestamps ---
        self.start_time_input = QLineEdit()
        self.end_time_input = QLineEdit()
        self.start_time_input.setPlaceholderText(
            "Début (hh:mm:ss ou mm:ss ou ss, ex: 1:01:01 ou 1:23 ou 45)"
        )
        self.end_time_input.setPlaceholderText(
            "Fin (hh:mm:ss ou mm:ss ou ss, ex: 1:22:04 ou 2:10 ou 75)"
        )
        form_layout.addRow("Début (&S) :", self.start_time_input)
        form_layout.addRow("Fin (&F):", self.end_time_input)

        # --- Saisie des questions/réponses (multiligne) ---
        self.questions_input = PlainPasteTextEdit()
        self.questions_input.setPlaceholderText(
            "Séparez par ; pour plusieurs questions"
        )
        form_layout.addRow("Questions (&Q) :", self.questions_input)
        self.responses_input = PlainPasteTextEdit()
        self.responses_input.setPlaceholderText("Séparez par ; pour plusieurs réponses")
        form_layout.addRow("Réponses (&R) :", self.responses_input)

        # --- Saisie de l'attribution ---
        self.attribution_input = QLineEdit()
        self.attribution_input.setPlaceholderText(
            "Attribution (optionnel, défaut: no-attribution)"
        )
        self.attribution_input.setText(self.last_attribution)
        form_layout.addRow("Attribution :", self.attribution_input)

        # --- Boutons principaux en ligne ---
        button_row = QHBoxLayout()

        # Bouton interroger ça
        ask_button = QPushButton("interroger ça (&C)")
        ask_button.setToolTip(
            "Sélectionnez un morceau de texte dans la question, puis cliquez ici : il sera remplacé par (?) dans la question et ajouté comme nouvelle réponse."
        )
        ask_button.setStyleSheet(
            "background-color: #b3e5fc; color: #01579b; font-weight: bold; border-radius: 6px;"
        )
        button_row.addWidget(ask_button)

        # Bouton mode rapide
        quick_button = QPushButton("mode rapide (&E)")
        quick_button.setToolTip(
            "Ajouter rapidement plusieurs entrées : chaque ligne saisie sera une entrée avec (?) comme question et la ligne comme réponse."
        )
        quick_button.setStyleSheet(
            "background-color: #3bb67d; color: white; font-weight: bold; border-radius: 6px;"
        )
        button_row.addWidget(quick_button)

        # Bouton de soumission
        self.submit_button = QPushButton("Soumettre (CTRL+S)")
        self.submit_button.setStyleSheet(
            "background-color: #1976d2; color: white; font-weight: bold; border-radius: 6px; border: 2px solid #388e3c;"
        )
        button_row.addWidget(self.submit_button)

        form_layout.addRow(button_row)

        def handle_ask():
            cursor = self.questions_input.textCursor()
            selected_text = cursor.selectedText()
            if not selected_text:
                QMessageBox.information(
                    self,
                    "Sélection requise",
                    "Veuillez sélectionner un texte dans la zone 'Questions' à interroger.",
                )
                return
            # Remplacer la sélection par (?) dans la question
            cursor.insertText("(?)")
            # Ajouter la réponse à responses_input (en fin, séparé par ; si besoin)
            resp = self.responses_input.toPlainText().strip()
            if resp:
                self.responses_input.setPlainText(resp + "; " + selected_text)
            else:
                self.responses_input.setPlainText(selected_text)

        ask_button.clicked.connect(handle_ask)

        def open_quick_dialog():
            quick_dialog = self._create_quick_dialog()
            quick_dialog.exec()

        quick_button.clicked.connect(open_quick_dialog)

        self.submit_button.clicked.connect(
            lambda: self.process_inputs(
                self.file_path_input,
                self.start_time_input,
                self.end_time_input,
                self.questions_input,
                self.responses_input,
                self.attribution_input,
            )
        )

        # Raccourci clavier Ctrl+S pour soumettre le formulaire
        submit_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        submit_shortcut.activated.connect(self.submit_button.click)

        # Ajout du formulaire au layout principal
        self.layout().addLayout(form_layout)

        self.showMaximized()  # Afficher la fenêtre principale en mode maximisé

    def _create_quick_dialog(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel

        quick_dialog = QDialog(self)
        quick_dialog.setWindowTitle("Mode rapide : saisie de plusieurs réponses")
        layout = QVBoxLayout(quick_dialog)
        layout.addWidget(QLabel("Saisissez une phrase par ligne :"))
        text_edit = PlainPasteTextEdit()
        layout.addWidget(text_edit)
        submit_btn = QPushButton("Ajouter toutes les entrées")
        layout.addWidget(submit_btn)

        # Ajout du raccourci clavier Ctrl+S pour submit_btn
        submit_shortcut = QShortcut(QKeySequence("Ctrl+S"), quick_dialog)
        submit_shortcut.activated.connect(submit_btn.click)

        # Ajout de la barre de progrès centralisée
        progress_helper = ProgressBarHelper(layout)

        submit_btn.clicked.connect(
            lambda: self._handle_quick_submit(text_edit, progress_helper, quick_dialog)
        )
        return quick_dialog

    def _handle_quick_submit(self, text_edit, progress_helper, quick_dialog):
        lines = [l.strip() for l in text_edit.toPlainText().splitlines() if l.strip()]
        if not lines:
            QMessageBox.warning(self, "Erreur", "Aucune phrase saisie.")
            return
        count = 0
        progress_helper.show(len(lines))
        for idx, word in enumerate(lines, start=1):
            try:
                self.db_manager.insert_record(
                    media_file="",
                    question="(?)",
                    response=word,
                    attribution="no-attribution",
                )
                count += 1
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur sur '{word}': {e}")
            progress_helper.set_value(idx)
        progress_helper.hide()
        QMessageBox.information(self, "Succès", f"{count} entrées ajoutées.")
        quick_dialog.accept()

    def safe_close(self):
        """Ferme l'application en toute sécurité si l'objet n'est pas supprimé."""
        if not self.isVisible():
            return
        self.close()

    def select_file(self, file_path_input):
        # Ouvre une boîte de dialogue pour sélectionner un fichier média (audio ou vidéo)
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner un fichier média",
            "",
            "Fichiers média (*.mp3 *.wav *.ogg *.mp4 *.avi *.mov *.mkv)",
        )
        if file_path:
            file_path_input.setText(file_path)
            self.last_audio_path = file_path  # Mémorise pour prochaines entrées

    def process_inputs(
        self,
        file_path_input,
        start_time_input,
        end_time_input,
        questions_input,
        responses_input,
        attribution_input,
    ):
        file_path = file_path_input.text()
        start_time_raw = start_time_input.text().strip()
        end_time_raw = end_time_input.text().strip()

        questions = [
            q.strip() for q in questions_input.toPlainText().split(";") if q.strip()
        ]
        responses = [
            r.strip() for r in responses_input.toPlainText().split(";") if r.strip()
        ]

        # --- Vérification explicite de l'existence du fichier média ---
        if file_path:
            if not os.path.exists(file_path):
                QMessageBox.critical(
                    self,
                    "Erreur",
                    f"Le fichier média spécifié n'existe pas : {file_path}",
                )
                return

        # --- Vérification de la validité des timestamps ---
        start_time = TimeUtils.parse_time_to_ms(start_time_raw)
        end_time = TimeUtils.parse_time_to_ms(end_time_raw)
        if start_time_raw and start_time is None:
            QMessageBox.warning(
                self,
                "Avertissement",
                f"Le format du timestamp de début est invalide. Saisie : {start_time_raw}",
            )
            return
        if end_time_raw and end_time is None:
            QMessageBox.warning(
                self,
                "Avertissement",
                f"Le format du timestamp de fin est invalide. Saisie : {end_time_raw}",
            )
            return
        # Affichage des valeurs converties (pour debug/UX)
        if start_time is not None:
            print(f"Début converti : {TimeUtils.ms_to_str(start_time)}")
        if end_time is not None:
            print(f"Fin converti : {TimeUtils.ms_to_str(end_time)}")

        question_data = "; ".join(questions) if questions else ""
        response_data = "; ".join(responses) if responses else ""
        attribution = attribution_input.text().strip() or "no-attribution"

        if not questions:
            QMessageBox.warning(
                self, "Avertissement", "Au moins une question est requise !"
            )
            return
        if not responses:
            QMessageBox.warning(
                self, "Avertissement", "Au moins une réponse est requise !"
            )
            return

        # Threading pour ne pas bloquer l'UI
        self.submit_button.setEnabled(False)
        self.submit_button.setText("Enregistrement...")
        # Lancer le worker qui appelle insert_record (qui gère le découpage si besoin)
        thread = QThread()
        worker = ProcessInputsWorker(
            self.db_manager,
            file_path,
            question_data,
            response_data,
            start_time,
            end_time,
            attribution,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self.on_process_inputs_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.start()
        # Garder une référence pour éviter la destruction prématurée
        if not hasattr(self, "_threads"):
            self._threads = []
        self._threads.append((thread, worker))

        # Nettoyer la liste après la fin du thread
        def cleanup():
            self._threads = [tw for tw in self._threads if tw[0].isRunning()]

        thread.finished.connect(cleanup)

    def on_process_inputs_finished(self, success, message):
        from PySide6.QtCore import QTimer

        def handle_result():
            self.submit_button.setEnabled(True)
            self.submit_button.setText("Soumettre (CTRL+S)")
            if success:
                self.file_path_input.setText(self.last_audio_path)
                self.start_time_input.clear()
                self.end_time_input.clear()
                self.questions_input.clear()
                self.responses_input.clear()
                self.last_attribution = (
                    self.attribution_input.text().strip() or "no-attribution"
                )
            else:
                QMessageBox.critical(self, "Erreur", message)

        QTimer.singleShot(0, handle_result)
