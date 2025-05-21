from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QMessageBox,
    QHBoxLayout,
    QLineEdit,
    QHeaderView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
import csv
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from common_methods import FavoritesManager, DialogUtils, ProgressBarHelper, MediaUtils
from logger import logger


class RecordManagerApp(QWidget):
    def __init__(self, db_manager, font_size=12):
        super().__init__()
        self.setWindowTitle("Gérer les entrées")
        self.db_manager = db_manager
        self.font_size = font_size
        self.setStyleSheet(f"* {{ font-size: {self.font_size}px; }}")
        self.changed_lines = set()
        self.setup_ui()
        self.showMaximized()

    def resize_table_columns(self):
        """Ajuste la largeur et le mode de redimensionnement des colonnes de la table."""
        header = self.table.horizontalHeader()
        header.resizeSection(0, 60)
        header.resizeSection(1, 60)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Champ de recherche
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher...")
        self.search_input.textChanged.connect(self.search_records)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        self.search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.search_shortcut.activated.connect(self.search_input.setFocus)

        # Section "Aller à la ligne"
        goto_layout = QHBoxLayout()
        self.line_input = QLineEdit()
        self.line_input.setPlaceholderText("Numéro de ligne...")
        goto_layout.addWidget(self.line_input)
        goto_button = QPushButton("Aller à la ligne")
        goto_button.clicked.connect(self.go_to_line)
        goto_layout.addWidget(goto_button)
        layout.addLayout(goto_layout)

        self.goto_shortcut = QShortcut(QKeySequence("Ctrl+G"), self)
        self.goto_shortcut.activated.connect(self.line_input.setFocus)

        # Table pour afficher les entrées
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            [
                "UUID",
                "Fichier Média",
                "Question",
                "Réponse",
                "Créé le",
                "Attribution",
                "Lire",
                "Favori",
            ]
        )
        self.table.itemChanged.connect(self.track_changes)
        layout.addWidget(self.table)

        self.resize_table_columns()

        self.progress_helper = ProgressBarHelper(layout)
        self.progress_helper.hide()

        # Boutons pour les actions
        button_layout = QHBoxLayout()
        save_button = QPushButton("Enregister/Actualiser (Ctrl+S)")
        save_button.clicked.connect(self.save_changes)
        button_layout.addWidget(save_button)

        delete_button = QPushButton("Supprimer (DELETE)")
        delete_button.clicked.connect(self.delete_record)
        button_layout.addWidget(delete_button)

        filter_error_button = QPushButton("Afficher les entrées signalé (&S)")
        filter_error_button.clicked.connect(self.filter_error_records)
        button_layout.addWidget(filter_error_button)

        filter_date_button = QPushButton("Filtrer par date (&F)")
        filter_date_button.setToolTip(
            "Filtrer les entrées par une plage de dates personnalisée."
        )
        filter_date_button.clicked.connect(self.filter_by_date_range)
        button_layout.addWidget(filter_date_button)

        clear_error_button = QPushButton("effacer les signalisations des erreurs (&D)")
        clear_error_button.clicked.connect(self.clear_error_file)
        button_layout.addWidget(clear_error_button)

        layout.addLayout(button_layout)

        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.save_changes)

        delete_shortcut = QShortcut(QKeySequence("Delete"), self)
        delete_shortcut.activated.connect(self.delete_record)

        edit_shortcut = QShortcut(QKeySequence("F2"), self)
        edit_shortcut.activated.connect(self.edit_selected_cell)

        close_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        close_shortcut.activated.connect(self.close)

        # Initialiser le lecteur média
        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)

        self.load_records()

    def focus_search_input(self):
        self.search_input.setFocus()

    def focus_line_input(self):
        self.line_input.setFocus()

    def track_changes(self, item):
        self.changed_lines.add(item.row())

    def closeEvent(self, event):
        if self.changed_lines:
            reply = QMessageBox.question(
                self,
                "Modifications non sauvegardées",
                "Voulez-vous sauvegarder les modifications avant de fermer?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save,
            )

            if reply == QMessageBox.Save:
                self.save_changes()
                event.accept()
            elif reply == QMessageBox.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def save_changes(self):
        visible_uuids = set()
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                uuid_item = self.table.item(row, 0)
                if uuid_item:
                    visible_uuids.add(uuid_item.text())

        changed_lines_copy = list(self.changed_lines)
        total_changes = len(changed_lines_copy)
        if total_changes == 0:
            QMessageBox.information(self, "Info", "Aucune modification à enregistrer.")
            self.load_records()
            return

        self.progress_helper.show(total_changes)
        for i, row in enumerate(changed_lines_copy):
            if (
                self.table.item(row, 0) is None
                or self.table.item(row, 2) is None
                or self.table.item(row, 3) is None
            ):
                self.changed_lines.discard(row)
                continue

            record_id = self.table.item(row, 0).text()
            new_media_file = self.table.item(row, 1).text()
            new_question = self.table.item(row, 2).text()
            new_response = self.table.item(row, 3).text()
            new_attribution = (
                self.table.item(row, 5).text()
                if self.table.item(row, 5)
                else "no-attribution"
            )

            try:
                success = self.db_manager.update_record(
                    record_id,
                    new_media_file,
                    new_question,
                    new_response,
                    new_attribution,
                )
                self.changed_lines.discard(row)
                if success:
                    logger.info(
                        f"entry UUID={record_id} is successfully modified by user."
                    )
                else:
                    raise Exception(f"Échec de la mise à jour pour UUID: {record_id}")
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))
                pass

            self.progress_helper.set_value(i + 1)

        self.progress_helper.hide()

        if not self.changed_lines:
            QMessageBox.information(
                self, "Succès", "Toutes les modifications ont été enregistrées."
            )
        self.table.blockSignals(True)
        self.load_records()
        self.table.blockSignals(False)

        for row in range(self.table.rowCount()):
            uuid_item = self.table.item(row, 0)
            if uuid_item and uuid_item.text() in visible_uuids:
                self.table.setRowHidden(row, False)
            else:
                self.table.setRowHidden(row, True)

        if self.search_input.text():
            self.search_records(self.search_input.text())

    def load_records(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        records = self.db_manager.fetch_all_records()
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            uuid_item = QTableWidgetItem(record["UUID"])
            uuid_item.setFlags(uuid_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, uuid_item)

            self.table.setItem(row, 1, QTableWidgetItem(record["media_file"]))

            self.table.setItem(row, 2, QTableWidgetItem(record["question"]))

            self.table.setItem(row, 3, QTableWidgetItem(record["response"]))

            creation_date_item = QTableWidgetItem(record["creation_date"])
            creation_date_item.setFlags(creation_date_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 4, creation_date_item)

            self.table.setItem(
                row, 5, QTableWidgetItem(record.get("attribution", "no-attribution"))
            )

            play_button = QPushButton("Lire")
            play_button.clicked.connect(
                lambda checked, media_file=record["media_file"]: self.play_media_file(
                    media_file
                )
            )
            self.table.setCellWidget(row, 6, play_button)

            fav_button = QPushButton("Favori")
            fav_button.setStyleSheet(
                "background-color: #ffd700; color: #333; font-weight: bold;"
            )
            fav_button.clicked.connect(
                lambda checked, uuid=record["UUID"]: FavoritesManager.mark_as_favorite(
                    self.db_manager, uuid, self
                )
            )
            self.table.setCellWidget(row, 7, fav_button)

        self.resize_table_columns()
        self.table.blockSignals(False)

    def play_media_file(self, media_file):
        MediaUtils.play_media_file_qt(self, media_file, self.media_player)

    def delete_record(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(
                self,
                "Erreur",
                "Veuillez sélectionner un ou plusieurs entrées à supprimer par CLIQUER sur les NUMÉROs des lignes.",
            )
            return

        rows_to_delete = sorted([index.row() for index in selected_rows], reverse=True)
        self.table.blockSignals(True)
        for row in rows_to_delete:
            record_id = self.table.item(row, 0).text()
            success = self.db_manager.delete_record(record_id)
            if not success:
                QMessageBox.critical(
                    self,
                    "Erreur",
                    f"Échec de la suppression de l'entrée UUID: {record_id}.",
                )
                self.table.blockSignals(False)
                return
            self.changed_lines.discard(row)
            self.changed_lines = set(
                (i - 1 if i > row else i) for i in self.changed_lines
            )

        self.table.blockSignals(False)
        QMessageBox.information(self, "Succès", "entrée(s) supprimé(s) avec succès.")
        self.load_records()

    def search_records(self, keyword):
        keyword = keyword.lower()
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            match = False
            for column in range(self.table.columnCount()):
                item = self.table.item(row, column)
                if item and keyword in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)
        self.table.blockSignals(False)

    def go_to_line(self):
        line_number_str = self.line_input.text()
        if not line_number_str.isdigit():
            QMessageBox.warning(
                self, "Erreur", "Veuillez entrer un numéro de ligne valide."
            )
            return

        line_number = int(line_number_str)
        if line_number < 1 or line_number > self.table.rowCount():
            QMessageBox.warning(
                self,
                "Erreur",
                f"Le numéro de ligne doit être entre 1 et {self.table.rowCount()}.",
            )
            return

        row_index = line_number - 1
        self.table.scrollToItem(self.table.item(row_index, 0))
        self.table.selectRow(row_index)
        self.line_input.clear()

    def filter_error_records(self):
        try:
            with open("entry_error.csv", "r", encoding="utf-8") as file:
                reader = csv.reader(file)
                error_uuids = {row[0] for row in reader}
            self.table.blockSignals(True)
            for row in range(self.table.rowCount()):
                uuid_item = self.table.item(row, 0)
                if uuid_item and uuid_item.text() in error_uuids:
                    self.table.setRowHidden(row, False)
                else:
                    self.table.setRowHidden(row, True)
            self.table.blockSignals(False)
            QMessageBox.information(self, "Info", "Filtrage des erreurs terminé.")
        except FileNotFoundError:
            QMessageBox.warning(
                self, "Erreur", "Le fichier entry_error.csv est introuvable."
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Une erreur s'est produite: {e}")

    def clear_error_file(self):
        try:
            with open("entry_error.csv", "w", encoding="utf-8") as file:
                pass
            QMessageBox.information(
                self, "Succès", "les signals ont été effacé avec succès."
            )
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Une erreur s'est produite: {e}")
        self.load_records()

    def edit_selected_cell(self):
        selected_items = self.table.selectedItems()
        if selected_items:
            self.table.editItem(selected_items[0])

    def filter_by_date_range(self):
        result = DialogUtils.select_date_range(self)
        if not result:
            return
        start, end = result
        records = self.db_manager.fetch_record_by_creation_date(start, end)
        if not records:
            QMessageBox.information(
                self, "Info", "Aucune entrée trouvée pour cette plage de dates."
            )
            return
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self.table.setRowCount(len(records))
        for row, record in enumerate(records):
            uuid_item = QTableWidgetItem(record["UUID"])
            uuid_item.setFlags(uuid_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, uuid_item)
            self.table.setItem(row, 1, QTableWidgetItem(record["media_file"]))
            self.table.setItem(row, 2, QTableWidgetItem(record["question"]))
            self.table.setItem(row, 3, QTableWidgetItem(record["response"]))
            creation_date_item = QTableWidgetItem(record["creation_date"])
            creation_date_item.setFlags(creation_date_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 4, creation_date_item)
            self.table.setItem(
                row, 5, QTableWidgetItem(record.get("attribution", "no-attribution"))
            )
            play_button = QPushButton("Lire")
            play_button.clicked.connect(
                lambda checked, media_file=record["media_file"]: self.play_media_file(
                    media_file
                )
            )
            self.table.setCellWidget(row, 6, play_button)
            fav_button = QPushButton("Favori")
            fav_button.setStyleSheet(
                "background-color: #ffd700; color: #333; font-weight: bold;"
            )
            fav_button.clicked.connect(
                lambda checked, uuid=record["UUID"]: FavoritesManager.mark_as_favorite(
                    self.db_manager, uuid, self
                )
            )
            self.table.setCellWidget(row, 7, fav_button)

        self.resize_table_columns()
        self.table.blockSignals(False)
