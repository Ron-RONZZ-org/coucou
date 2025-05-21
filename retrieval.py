# Astuce VSCode :
# Pour aller directement à la définition d'une fonction (et non à toutes les références),
# utilisez F12 ou clic droit > "Aller à la définition". Assurez-vous que l'extension Python est activée.
# Si VSCode montre toutes les références au lieu de la définition, vérifiez que le code est bien formaté
# et que les extensions de langage sont à jour.
#
# Ce fichier est structuré pour que VSCode détecte correctement les définitions de fonctions et de classes.
#
# ---

import difflib
import os
import unicodedata
import string
import json  # Importer le module JSON pour la sauvegarde et la restauration
import csv  # Importer le module CSV pour enregistrer les erreurs
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QMessageBox,
    QDialog,
    QFileDialog,  # Importer QFileDialog pour sélectionner un fichier
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import (
    Qt,
    QTimer,  # Importer QTimer pour gérer les délais
)  # Importer QDate pour gérer les dates Qt et Qt pour les options de fenêtre
from PySide6.QtGui import QShortcut, QKeySequence  # Importer QShortcut et QKeySequence
from logger import logger  # Remplacer l'import de logging par le logger centralisé
import re
from common_methods import FavoritesManager, DialogUtils, TextUtils, MediaUtils


class RetrievalApp(QWidget):
    # --- Initialisation et configuration générale ---
    def __init__(self, db_manager, font_size=12, review_mode=False):
        super().__init__()
        self.db_manager = db_manager
        self.font_size = font_size
        self.review_mode = review_mode
        self.records = None
        self.current_record_index = 0
        self.current_dialog = None
        self.autoplay_enabled = False
        self._video_dialog_ref = type(
            "VideoDialogRef", (), {}
        )()  # Pour la gestion centralisée vidéo
        self._video_dialog_ref.dialog = None
        self._setup_window()
        self._setup_layout()
        self._setup_shortcuts()
        self._setup_audio()
        logger.info("Interface RetrievalApp initialisée")
        self.show_setup_dialog()

    def _setup_window(self):
        self.setWindowTitle("Afficher les éléments")
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowSystemMenuHint
        )
        self.setStyleSheet(f"* {{ font-size: {self.font_size}px; }}")

    def _setup_layout(self):
        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)

    def _setup_shortcuts(self):
        close_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        close_shortcut.activated.connect(self.close)
        logger.info("Raccourci Ctrl+W ajouté pour fermer la fenêtre")

    def _setup_audio(self):
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.playbackStateChanged.connect(self.on_audio_state_changed)

    # --- Gestion des fichiers de session (sauvegarde/restauration) ---
    def save_records_to_file(self, file_path="saved_records.json"):
        try:
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(self.records, file, ensure_ascii=False, indent=4)
            logger.info(f"Enregistrements sauvegardés dans {file_path}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des enregistrements: {e}")
            QMessageBox.critical(
                self, "Erreur", "Impossible de sauvegarder les enregistrements!"
            )

    def load_records_from_file(self, file_path="saved_records.json"):
        try:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as file:
                    self.records = json.load(file)
                logger.info(f"Enregistrements chargés depuis {file_path}")
                return True
            else:
                logger.warning(f"Fichier {file_path} introuvable.")
                return False
        except Exception as e:
            logger.error(f"Erreur lors du chargement des enregistrements: {e}")
            QMessageBox.critical(
                self, "Erreur", "Impossible de charger les enregistrements!"
            )
            return False

    def save_records_to_custom_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Sauvegarder les enregistrements", "", "JSON Files (*.json)"
        )
        if file_path:
            self.save_records_to_file(file_path)

    def load_records_from_custom_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Charger les enregistrements", "", "JSON Files (*.json)"
        )
        if file_path:
            return self.load_records_from_file(file_path)
        return False

    def saved_session_overwirte_warning(self):
        if (
            os.path.exists("saved_records.json")
            and os.path.getsize("saved_records.json") > 0
        ):
            overwrite_warning = QMessageBox.question(
                self,
                "Attention",
                "Une session précédente interrompu est sauvegardé automatiquement et peut être restaurée. Vous perdrez la session dont tous les progrès si vous démarrez une nouvelle session. "
                "Continuez ?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if overwrite_warning == QMessageBox.No:
                return True
        return False

    # --- Sélection et chargement des enregistrements (UI d'entrée) ---
    def show_setup_dialog(self):
        if (
            os.path.exists("saved_records.json")
            and os.path.getsize("saved_records.json") > 0
        ):
            reply = QMessageBox.question(
                self,
                "Session précédente détectée",
                "Une session précédente a été auto-sauvegardée. Voulez-vous la restaurer ?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                if self.load_records_from_file():
                    self.refresh_records_from_db()
                    self.initialize_ui()
                    return

        self.current_dialog = QDialog(self)
        self.current_dialog.setWindowTitle("Sélectionner une option")
        layout = QVBoxLayout(self.current_dialog)

        label = QLabel(
            "Voulez-vous afficher tous les enregistrements, une gamme de dates spécifique, les favoris ou restaurer une session précédente ?"
        )
        layout.addWidget(label)

        date_range_button = QPushButton("Afficher une gamme de dates")
        date_range_button.clicked.connect(
            lambda: self.handle_date_range_selection(self.current_dialog)
        )
        layout.addWidget(date_range_button)

        all_records_button = QPushButton("Afficher tous les enregistrements")
        all_records_button.clicked.connect(
            lambda: self.handle_all_records_selection(self.current_dialog)
        )
        layout.addWidget(all_records_button)

        favorites_button = QPushButton("Afficher les favoris")
        favorites_button.clicked.connect(
            lambda: (self.current_dialog.accept(), self.load_favorite_records())
        )
        layout.addWidget(favorites_button)

        restore_session_button = QPushButton("Restaurer la session précédente")
        restore_session_button.clicked.connect(
            lambda: self.handle_restore_session(self.current_dialog)
        )
        layout.addWidget(restore_session_button)

        self.current_dialog.exec()

    def handle_date_range_selection(self, dialog):
        if self.saved_session_overwirte_warning():
            return
        dialog.accept()
        result = DialogUtils.select_date_range(self)
        if not result:
            return
        start, end = result
        self.records = self.db_manager.fetch_record_by_creation_date(start, end)
        if self.records:
            self.initialize_ui()
        else:
            QMessageBox.information(self, "Info", "Aucun entrée trouvé.")
            self.show_setup_dialog()

    def handle_all_records_selection(self, dialog):
        if self.saved_session_overwirte_warning():
            return
        dialog.accept()
        self.records = self.db_manager.fetch_all_records()
        if self.records:
            self.initialize_ui()
        else:
            QMessageBox.information(
                self,
                "Info",
                "Aucun entrée trouvé. Veuillez ajouter les entrées d'abord",
            )
            self.close()

    def handle_restore_session(self, dialog):
        dialog.accept()
        use_custom_file = QMessageBox.question(
            self,
            "Restaurer",
            "Voulez-vous charger depuis un fichier personnalisé ?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if use_custom_file == QMessageBox.Yes:
            success = self.load_records_from_custom_file()
        else:
            success = self.load_records_from_file()

        if success:
            if self.records:
                self.refresh_records_from_db()
                self.initialize_ui()
            else:
                QMessageBox.information(
                    self, "Info", "Aucun enregistrement à restaurer."
                )
                self.show_setup_dialog()
        else:
            QMessageBox.warning(
                self, "Erreur", "Impossible de restaurer la session précédente."
            )
            self.show_setup_dialog()

    # --- Interface principale de révision ---
    def initialize_ui(self):
        self.showMaximized()
        self.display_next_item()

    def display_next_item(self):
        while self.main_layout.count():
            child = self.main_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not self.records:
            self.update_usage_stats()  # Enregistrer la fin de session
            if os.path.exists("saved_records.json"):
                try:
                    os.remove("saved_records.json")
                    logger.info(
                        "Fichier saved_records.json supprimé après la fin de la session."
                    )
                except Exception as e:
                    logger.error(
                        f"Erreur lors de la suppression de saved_records.json: {e}"
                    )
            self.play_audio("assets/audio_effects/félicitations.ogg")
            end_label = QLabel("Tout fait! Félicitations! ✨ 🌟 ✨")
            end_label.setAlignment(Qt.AlignCenter)
            self.main_layout.addWidget(end_label)
            close_button = QPushButton("Fermer")
            close_button.clicked.connect(self.close)
            self.main_layout.addWidget(close_button)
            return

        record = self.records[self.current_record_index]

        if not hasattr(self, "_initial_record_count"):
            self._initial_record_count = len(self.records)
        progress = (
            1 - (len(self.records) / self._initial_record_count)
            if self._initial_record_count
            else 1
        )
        percent = int(progress * 100)
        progress_label = QLabel(f"Progression : {percent}%")
        progress_label.setAlignment(Qt.AlignRight)
        self.main_layout.addWidget(progress_label)

        questions = [q.strip() for q in record["question"].split(";") if q.strip()]
        responses = [r.strip() for r in record["response"].split(";") if r.strip()]
        audio_path = record["media_file"]
        entry_uuid = record.get("UUID", "unknown_uuid")

        # Affichage commun (questions/réponses, audio, boutons)
        if getattr(self, "review_mode", False):
            self._show_questions_with_responses(questions, responses)
        else:
            self.response_inputs = []
            question_widgets = []
            response_idx = 0
            first_input = None
            for idx, q in enumerate(questions):
                if "(?)" in q:
                    num_blanks = q.count("(?)")
                    placeholders = [
                        "<span style='color:#888;'>______</span>"
                    ] * num_blanks

                    def make_question_html(q, values):
                        parts = q.split("(?)")
                        html = ""
                        for i, part in enumerate(parts):
                            html += part
                            if i < len(values):
                                html += f"<b><span style='color:#1976d2;'>{values[i] if values[i] else '______'}</span></b>"
                        return html

                    current_values = [""] * num_blanks
                    question_label = QLabel()
                    question_label.setTextFormat(Qt.RichText)
                    question_label.setWordWrap(True)
                    question_label.setAlignment(Qt.AlignHCenter)
                    question_label.setText(make_question_html(q, current_values))
                    self.main_layout.addWidget(question_label)
                    blank_inputs = []
                    for i in range(num_blanks):
                        correct_resp = (
                            responses[response_idx]
                            if response_idx < len(responses)
                            else ""
                        )
                        if hasattr(self, "fontMetrics"):
                            width = (
                                self.fontMetrics().horizontalAdvance(correct_resp) + 18
                            )
                        else:
                            width = max(60, min(300, 10 * len(correct_resp) + 18))
                        response_input = QLineEdit()
                        response_input.setMinimumWidth(width)
                        response_input.setMaximumWidth(width)
                        response_input.setAlignment(Qt.AlignCenter)
                        response_input.setStyleSheet(
                            "margin:4px 0 12px 0;padding:2px 6px;"
                        )
                        self.response_inputs.append(response_input)
                        blank_inputs.append(response_input)
                        response_idx += 1
                        self.main_layout.addWidget(
                            response_input, alignment=Qt.AlignHCenter
                        )
                        if first_input is None:
                            first_input = response_input

                    def update_label():
                        values = [edit.text() for edit in blank_inputs]
                        question_label.setText(make_question_html(q, values))

                    for edit in blank_inputs:
                        edit.textChanged.connect(update_label)
                    update_label()
                else:
                    label = QLabel(f"{idx+1}. {q}")
                    self.main_layout.addWidget(label)
                    response_input = QLineEdit()
                    self.main_layout.addWidget(response_input)
                    self.response_inputs.append(response_input)
                    response_idx += 1
                    if first_input is None:
                        first_input = response_input
            if first_input is not None:
                first_input.setFocus()

        play_button = QPushButton("Lire l'audio (&A)")
        play_button.setStyleSheet(
            "background-color: #b3e5fc; color: #01579b; font-weight: bold;"
        )
        play_button.clicked.connect(lambda: self.play_audio(audio_path))
        self.main_layout.addWidget(play_button)

        favorite_button = QPushButton("Favori (&F)")
        favorite_button.setStyleSheet(
            "background-color: #ffd700; color: #333; font-weight: bold;"
        )
        favorite_button.clicked.connect(lambda: self.mark_as_favorite(entry_uuid))
        self.main_layout.addWidget(favorite_button)

        report_error_button = QPushButton("Signaler une erreur (&E)")
        report_error_button.setStyleSheet(
            "background-color: #c14a6c; color: white; font-weight: bold;"
        )
        report_error_button.clicked.connect(lambda: self.report_error(entry_uuid))
        self.main_layout.addWidget(report_error_button)

        if getattr(self, "review_mode", False):
            skip_button = QPushButton("Sauter (&K)")
            skip_button.setStyleSheet(
                "background-color: #e0e0e0; color: #222; font-weight: bold;"
            )
            skip_button.clicked.connect(self.skip_current_entry)
            self.main_layout.addWidget(skip_button)
            from PySide6.QtWidgets import QCheckBox

            autoplay_checkbox = QCheckBox("Lecture auto (autoplay) (&L)")
            autoplay_checkbox.setChecked(self.autoplay_enabled)

            def toggle_autoplay(state):
                self.autoplay_enabled = bool(state)

            autoplay_checkbox.stateChanged.connect(toggle_autoplay)
            self.main_layout.addWidget(autoplay_checkbox)
            return
        # Mode normal : boutons spécifiques
        enter_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self)
        enter_shortcut.activated.connect(
            lambda correct_responses=responses: self.check_multiple_responses_dialog(
                correct_responses, None
            )
        )
        submit_button = QPushButton("Vérifier les réponses (&C)")
        submit_button.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; border: 2px solid #388e3c;"
        )
        submit_button.clicked.connect(
            lambda _, correct_responses=responses: self.check_multiple_responses_dialog(
                correct_responses, None
            )
        )
        self.main_layout.addWidget(submit_button)
        save_custom_button = QPushButton(
            "Sauvegarder le progrès dans un fichier personnalisé (&S)"
        )
        save_custom_button.setStyleSheet(
            "background-color: #3bb67d; color: white; font-weight: bold;"
        )
        save_custom_button.clicked.connect(self.save_records_to_custom_file)
        self.main_layout.addWidget(save_custom_button)
        refresh_button = QPushButton("Actualiser les entrées (&R)")
        refresh_button.setStyleSheet(
            "background-color: #4f4dc9; color: white; font-weight: bold;"
        )
        refresh_button.clicked.connect(
            lambda: (self.refresh_records_from_db(), self.display_next_item())
        )
        self.main_layout.addWidget(refresh_button)
        skip_button = QPushButton("Sauter (&K)")
        skip_button.setStyleSheet(
            "background-color: #e0e0e0; color: #222; font-weight: bold;"
        )
        skip_button.clicked.connect(self.skip_current_entry)
        self.main_layout.addWidget(skip_button)
        self.save_records_to_file()  # sauvegarder progrès en cas de crash

        # Lancer la lecture du média seulement après que l'UI soit complètement chargée
        QTimer.singleShot(0, lambda: self.play_audio(audio_path))

    # --- Actualisation et gestion des entrées ---
    def refresh_records_from_db(self):
        updated_records = []
        logger.warning("Essayer d'actualiser les entrées...")
        for record in self.records:
            uuid = record.get("UUID")
            if uuid:
                updated_record = self.db_manager.fetch_record_by_uuid(uuid)
                if updated_record:
                    updated_records.append(updated_record)
                else:
                    logger.warning(f"Enregistrement introuvable pour UUID: {uuid}")
        self.records = updated_records

        QMessageBox.information(self, "Info", "Les entrées ont été actualisées.")

    # --- Signalement d'erreur sur une entrée ---
    def report_error(self, entry_uuid=None):
        if entry_uuid is None:
            current_record = self.records[self.current_record_index]
            entry_uuid = current_record.get("UUID", "unknown_uuid")
        try:
            with open("entry_error.csv", "a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow([entry_uuid])
            logger.info(f"Erreur signalée pour l'UUID: {entry_uuid}")
            QMessageBox.information(self, "Succès", "Erreur signalée avec succès!")
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement de l'UUID: {e}")
            QMessageBox.critical(self, "Erreur", "Impossible de signaler l'erreur!")

    def mark_as_favorite(self, entry_uuid=None):
        if entry_uuid is None:
            current_record = self.records[self.current_record_index]
            entry_uuid = current_record.get("UUID", "unknown_uuid")
        return FavoritesManager.mark_as_favorite(
            self.db_manager, entry_uuid, self, logger
        )

    def load_favorite_records(self):
        records = FavoritesManager.load_favorite_records(self.db_manager, self, logger)
        if records:
            self.records = records
            self.initialize_ui()
            return True
        return False

    # --- Utilitaires de comparaison et normalisation de texte ---
    @staticmethod
    def normalize_text(text):
        text = text.lower().strip().replace("ỹ", "y")
        text = TextUtils.normalize_special_characters(text)
        text = unicodedata.normalize("NFKC", text)
        text = text.translate(str.maketrans("", "", string.punctuation + "’' ‘«»–"))
        return text

    @staticmethod
    def html_diff(a: str, b: str):
        import string
        import html

        def strip_punct(text):
            return "".join(
                ch for ch in text if ch not in string.punctuation + "’' ‘«»–"
            )

        def build_index_map(text):
            idx_map = []
            count = 0
            for i, ch in enumerate(text):
                if ch not in string.punctuation + "’' ‘«»–":
                    idx_map.append(i)
                    count += 1
            return idx_map

        a_stripped = strip_punct(a)
        b_stripped = strip_punct(b)
        seqm = difflib.SequenceMatcher(None, a_stripped.lower(), b_stripped.lower())
        a_idx_map = build_index_map(a)
        b_idx_map = build_index_map(b)
        a_html = ""
        b_html = ""
        a_last = 0
        b_last = 0
        for opcode, a0, a1, b0, b1 in seqm.get_opcodes():
            a_start = a_idx_map[a0] if a0 < len(a_idx_map) else len(a)
            a_end = (
                a_idx_map[a1 - 1] + 1
                if a1 - 1 < len(a_idx_map) and a1 > a0
                else a_start
            )
            b_start = b_idx_map[b0] if b0 < len(b_idx_map) else len(b)
            b_end = (
                b_idx_map[b1 - 1] + 1
                if b1 - 1 < len(b_idx_map) and b1 > b0
                else b_start
            )
            a_html += html.escape(a[a_last:a_start])
            b_html += html.escape(b[b_last:b_start])
            if opcode == "equal":
                a_html += html.escape(a[a_start:a_end])
                b_html += html.escape(b[b_start:b_end])
            elif opcode == "replace":
                a_html += f"<u style='background: #ff0000; color: #fff;'>{html.escape(a[a_start:a_end])}</u>"
                b_html += f"<u style='background: #00b300; color: #fff;'>{html.escape(b[b_start:b_end])}</u>"
            elif opcode == "insert":
                b_html += f"<u style='background: #00b300; color: #fff;'>{html.escape(b[b_start:b_end])}</u>"
            elif opcode == "delete":
                a_html += f"<u style='background: #ff0000; color: #fff;'>{html.escape(a[a_start:a_end])}</u>"
            a_last = a_end
            b_last = b_end
        a_html += html.escape(a[a_last:])
        b_html += html.escape(b[b_last:])
        return a_html, b_html

    # --- Vérification de la réponse utilisateur ---
    def check_multiple_responses_dialog(self, correct_responses, dialog=None):
        if self.review_mode:
            self.update_usage_stats()
            self.records.pop(self.current_record_index)
        else:
            user_responses = [
                TextUtils.normalize_special_characters(edit.text().strip())
                for edit in self.response_inputs
            ]
            if len(user_responses) != len(correct_responses):
                QMessageBox.warning(self, "Erreur", "Nombre de réponses incorrect.")
                return
            if any(resp == "" for resp in user_responses):
                QMessageBox.warning(self, "Erreur", "Aucune réponse ne doit être vide.")
                return
            correct_count = 0
            total = len(correct_responses)
            detailed_results = []
            for user, correct in zip(user_responses, correct_responses):
                is_correct = False
                if re.fullmatch(r"\s*[+-]?\s*\d*(\.\d+)?\s*%?\s*", correct):
                    try:
                        correct_response_processed = (
                            float(correct.strip("%")) / 100
                            if "%" in correct
                            else float(correct)
                        )
                        user_response_processed = (
                            float(user.strip("%")) / 100 if "%" in user else float(user)
                        )
                        if (
                            abs(user_response_processed - correct_response_processed)
                            < 0.01
                        ):
                            is_correct = True
                    except ValueError:
                        pass
                else:
                    user_mod = TextUtils.normalize_special_characters(user)
                    correct_mod = TextUtils.normalize_special_characters(correct)
                    match = re.match(r"^(.*?)(\(.*?\))(.*?)$", correct_mod)
                    if match:
                        base = match.group(1) + match.group(3)
                        paren = match.group(2)
                        optional_list = paren.strip("()").split(" ")
                        for opt in optional_list:
                            user_processed = user_mod.replace(opt, "")
                            correct_processed = base.replace(opt, "")
                            user_processed = self.normalize_text(user_processed)
                            correct_processed = self.normalize_text(correct_processed)
                            if user_processed == correct_processed:
                                is_correct = True
                                break
                    else:
                        user_processed = self.normalize_text(user_mod)
                        correct_processed = self.normalize_text(correct_mod)
                        if user_processed == correct_processed:
                            is_correct = True
                if is_correct:
                    correct_count += 1
                detailed_results.append(is_correct)
            all_correct = correct_count == total
            self.update_usage_stats(correct_count, total)
            if all_correct:
                self.play_audio("assets/audio_effects/correct.ogg")
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Succès")
                msg_box.setText(
                    f"Toutes les réponses sont correctes ! ({correct_count}/{total})"
                )
                msg_box.setIcon(QMessageBox.Information)
                QTimer.singleShot(1000, msg_box.accept)  # Fermeture auto après 1s
                msg_box.exec()
                self.records.pop(self.current_record_index)
            else:
                self.play_audio("assets/audio_effects/error.ogg")
                QTimer.singleShot(
                    800,
                    lambda: self.play_audio(
                        self.records[self.current_record_index]["media_file"]
                    ),
                )
                diff_html = (
                    f"<b>{correct_count}/{total} réponses correctes.</b><br><br>"
                )
                incorrects = [
                    (idx, user, correct)
                    for idx, (user, correct, is_ok) in enumerate(
                        zip(user_responses, correct_responses, detailed_results)
                    )
                    if not is_ok
                ]
                for i, (idx, user, correct) in enumerate(incorrects):
                    user_diff, correct_diff = self.html_diff(user, correct)
                    diff_html += f"<b>Réponse {idx+1} :</b><br>"
                    diff_html += f"Votre réponse : <span style='color: orange;'>{user_diff}</span><br>"
                    diff_html += f"Réponse attendue : <span style='color: green;'>{correct_diff}</span>"
                    if i != len(incorrects) - 1:
                        diff_html += "<br><br>"
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Erreur")
                msg_box.setText(
                    f"<b>Au moins une réponse est incorrecte.</b><br><br>{diff_html}<br><small>Les différences sont soulignées.</small>"
                )
                msg_box.setTextFormat(Qt.RichText)
                entry_uuid = self.records[self.current_record_index].get(
                    "UUID", "unknown_uuid"
                )
                report_button = msg_box.addButton(
                    "Signaler une erreur", QMessageBox.ActionRole
                )
                # Ajout du bouton Continuer
                continue_button = msg_box.addButton("Continuer", QMessageBox.AcceptRole)

                def report_and_close():
                    self.report_error(entry_uuid)
                    msg_box.done(0)

                report_button.clicked.connect(report_and_close)
                msg_box.exec()
                self.records.append(self.records.pop(self.current_record_index))
        self.stop_audio(dialog)
        self.display_next_item()

    # --- Gestion audio et vidéo ---
    def play_audio(self, media_path):
        # Arrêter toute lecture en cours avant de lancer une nouvelle
        try:
            if self.media_player.playbackState() == QMediaPlayer.PlayingState:
                self.media_player.stop()
                # Forcer la réinitialisation de la source pour certains bugs Linux
                self.media_player.setSource(None)
        except Exception:
            pass
        MediaUtils.play_media_file_qt(
            self, media_path, self.media_player, self._video_dialog_ref
        )

    def stop_audio(self, dialog=None):
        try:
            if self.media_player.isPlaying():
                logger.info("Arrêt de la lecture média.")
                self.media_player.stop()
        except Exception:
            pass
        if dialog:
            dialog.accept()

    def on_audio_state_changed(self, state):
        if (
            getattr(self, "review_mode", False)
            and getattr(self, "autoplay_enabled", False)
            and state == QMediaPlayer.StoppedState
        ):
            if self.records:
                self.records.pop(self.current_record_index)
                self.display_next_item()

    # --- Fermeture propre de l'application ---
    def closeEvent(self, event):
        if self.records:
            self.save_records_to_file()
        logger.info("Fermeture de session de revoir.")
        self.media_player.stop()
        super().closeEvent(event)
        self.deleteLater()

    def skip_current_entry(self):
        """Affiche les réponses correctes pendant 1s avant de sauter à la prochaine entrée."""
        if not self.records:
            return
        record = self.records[self.current_record_index]
        questions = [q.strip() for q in record["question"].split(";") if q.strip()]
        responses = [r.strip() for r in record["response"].split(";") if r.strip()]
        self._show_questions_with_responses(questions, responses)
        QTimer.singleShot(
            1000,
            lambda: (
                self.records.pop(self.current_record_index),
                self.display_next_item(),
            ),
        )

    def _show_questions_with_responses(self, questions, responses):
        """Affiche les questions et leurs réponses correctes dans le layout principal.
        Les questions avec des (?) sont reconstruites avec les réponses insérées et centrées.
        Le tout est centré verticalement et horizontalement."""
        # Nettoyer le layout
        while self.main_layout.count():
            child = self.main_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        response_idx = 0
        self.main_layout.addStretch(1)  # Centrage vertical (avant)
        for idx, q in enumerate(questions):
            if "(?)" in q:
                num_blanks = q.count("(?)")
                inserted = []
                for i in range(num_blanks):
                    if response_idx < len(responses):
                        inserted.append(
                            f"<b style='color:green'>{responses[response_idx]}</b>"
                        )
                        response_idx += 1
                    else:
                        inserted.append("<b style='color:green'>______</b>")
                parts = q.split("(?)")
                html = ""
                for i, part in enumerate(parts):
                    html += part
                    if i < len(inserted):
                        html += inserted[i]
                label = QLabel(html)
                label.setTextFormat(Qt.RichText)
                label.setWordWrap(True)
                label.setAlignment(Qt.AlignHCenter)
                self.main_layout.addWidget(label)
            else:
                label = QLabel(f"{idx+1}. {q}")
                self.main_layout.addWidget(label)
                if response_idx < len(responses):
                    resp_label = QLabel(
                        f"<b style='color:green'>{responses[response_idx]}</b>"
                    )
                    resp_label.setTextFormat(Qt.RichText)
                    self.main_layout.addWidget(resp_label)
                    response_idx += 1
        self.main_layout.addStretch(1)  # Centrage vertical (après)

    # --- Mise à jour des statistiques d'utilisation ---
    def update_usage_stats(self, correct_count=None, total_count=None):
        import datetime

        stats_file = "usage_stats.json"
        today = datetime.date.today().isoformat()
        stats = {
            "retrieval_count": 0,
            "review_count": 0,
            "correct_count": 0,
            "answered_count": 0,
            "dates": [],
        }
        if os.path.exists(stats_file):
            try:
                with open(stats_file, "r", encoding="utf-8") as f:
                    stats.update(json.load(f))
            except Exception:
                pass
        if self.review_mode:
            stats["review_count"] += 1
        else:
            stats["retrieval_count"] += 1
            if correct_count is not None and total_count is not None:
                stats["correct_count"] += correct_count
                stats["answered_count"] += total_count
        if not stats["dates"] or stats["dates"][-1] != today:
            stats["dates"].append(today)
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
