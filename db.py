from __future__ import annotations

from PySide6.QtSql import QSqlDatabase, QSqlQuery
from PySide6.QtWidgets import QMessageBox
from datetime import date, datetime
import uuid
from gtts import gTTS  # Importer gTTS pour générer des fichiers audio
import os


class DatabaseManager:
    @staticmethod
    def cleanup_connections():
        """Supprime toutes les connexions SQLite existantes."""
        while QSqlDatabase.contains("qt_sql_default_connection"):
            try:
                QSqlDatabase.removeDatabase("qt_sql_default_connection")
            except RuntimeError:
                pass  # Ignorer si la connexion est encore utilisée

    def __init__(self, db_name: str):
        try:
            # Nettoyer les connexions existantes avant d'en créer une nouvelle
            self.connection_name = (
                f"connection_{uuid.uuid4()}"  # Utiliser une connexion unique
            )
            self.db = QSqlDatabase.addDatabase("QSQLITE", self.connection_name)
            self.db.setDatabaseName(db_name)
            if not self.db.open():
                raise Exception("Failed to open database")

            self.create_tables()
        except Exception as e:
            QMessageBox.critical(None, "Erreur", str(e))

    def create_tables(self):
        query = QSqlQuery(self.db)  # Associer la requête à la connexion nommée
        query.exec_(
            """
            CREATE TABLE IF NOT EXISTS records (
                UUID TEXT PRIMARY KEY,
                audio_file TEXT NOT NULL,
                question TEXT NOT NULL,
                response TEXT NOT NULL,
                creation_date TEXT NOT NULL,
                custom_audio INTEGER DEFAULT 0  -- Nouvelle colonne pour indiquer si l'audio est personnalisé
            )
            """
        )

    def auto_generate_audio(self, question: str, response: str) -> str:
        """Génère un fichier audio basé sur la question et la réponse."""
        save_dir = "assets/audio/"
        os.makedirs(save_dir, exist_ok=True)
        audio_text = question.replace("(?)", response)
        file_name = f"{response[:20].replace(' ', '_')}.mp3"
        audio_file_path = os.path.join(save_dir, file_name)
        tts = gTTS(text=audio_text, lang="fr")
        try:
            tts.save(audio_file_path)
        except Exception as e:
            raise Exception(f"Échec de la génération de l'audio : {e}")
        return audio_file_path

    def insert_record(
        self,
        audio_file: str,
        question: str,
        response: str,
        UUID: str = None,
        creation_date: str = None,
    ):
        try:
            UUID = UUID or str(uuid.uuid4())  # Générer un ID unique si non fourni
            if creation_date:
                # Convertir la date fournie dans le format attendu
                try:
                    datetime.strptime(creation_date, "%Y-%m-%d")
                except ValueError:
                    raise Exception("Le format de la date doit être 'YYYY-MM-DD'")
            else:
                creation_date = datetime.now().strftime(
                    "%Y-%m-%d"
                )  # Générer la date actuelle si non fournie

            if not audio_file:  # Si aucun fichier audio n'est fourni
                audio_file = self.auto_generate_audio(question, response)
                custom_audio = 0  # Audio généré automatiquement
            else:  # Si un fichier audio est fourni
                save_dir = "assets/audio/"
                os.makedirs(save_dir, exist_ok=True)
                file_name = os.path.basename(audio_file)
                save_path = os.path.join(save_dir, file_name)
                try:
                    with open(audio_file, "rb") as src, open(save_path, "wb") as dst:
                        dst.write(src.read())
                except Exception as e:
                    raise Exception(f"Échec de la sauvegarde de l'audio fourni : {e}")
                audio_file = save_path
                custom_audio = 1  # Audio fourni par l'utilisateur

            # Vérifier si un entrée avec la même question et réponse existe déjà
            query = QSqlQuery(self.db)
            query.prepare(
                """
                SELECT COUNT(*) FROM records
                WHERE question = ? AND response = ?
                """
            )
            query.addBindValue(question)
            query.addBindValue(response)
            if not query.exec_():
                raise Exception(
                    f"Failed to check for duplicate record: {query.lastError().text()}"
                )

            query.next()
            if query.value(0) > 0:  # Si un entrée existe déjà
                return 1  # Ne pas insérer de doublon

            # Insérer le nouvel entrée
            query.prepare(
                """
                INSERT INTO records (UUID, audio_file, question, response, creation_date, custom_audio)
                VALUES (?, ?, ?, ?, ?, ?)
                """
            )
            query.addBindValue(UUID)
            query.addBindValue(audio_file)
            query.addBindValue(question)
            query.addBindValue(response)
            query.addBindValue(creation_date)
            query.addBindValue(custom_audio)  # Ajouter la valeur de custom_audio
            if not query.exec_():
                return 1
                raise Exception(f"Failed to insert record: {query.lastError().text()}")
            else:
                return 0
        except Exception as e:
            QMessageBox.critical(None, "Erreur", str(e))

    def fetch_all_records(self):
        try:
            query = QSqlQuery(self.db)  # Associer la requête à la connexion nommée
            query.exec_(
                "SELECT UUID, audio_file, question, response, creation_date FROM records"
            )
            records = []
            while query.next():
                records.append(
                    {
                        "UUID": query.value(0),  # Assurez-vous que 'UUID' est inclus
                        "audio_file": query.value(1),
                        "question": query.value(2),
                        "response": query.value(3),
                        "creation_date": query.value(4),
                    }
                )
            return records
        except Exception as e:
            QMessageBox.critical(None, "Erreur", str(e))

    def fetch_record_by_creation_date(self, start: date, finish: date):
        try:
            query = QSqlQuery(self.db)  # Associer la requête à la connexion nommée
            query.prepare(
                """
                SELECT * FROM records
                WHERE creation_date BETWEEN ? AND ?
                """
            )
            query.addBindValue(start.isoformat())
            query.addBindValue(finish.isoformat())
            if not query.exec_():
                raise Exception(f"Failed to fetch records: {query.lastError().text()}")

            records = []
            while query.next():
                records.append(
                    {
                        "UUID": query.value(0),
                        "audio_file": query.value(1),
                        "question": query.value(2),
                        "response": query.value(3),
                        "creation_date": query.value(4),
                    }
                )
            return records
        except Exception as e:
            QMessageBox.critical(None, "Erreur", str(e))

    def update_record(
        self, record_id: str, new_audio_file: str, new_question: str, new_response: str
    ) -> bool:
        try:
            """Met à jour un entrée existant dans la base de données."""
            # Récupérer l'entrée existante
            query = QSqlQuery(self.db)
            query.prepare(
                """
                SELECT audio_file, question, response, custom_audio FROM records WHERE UUID = ?
                """
            )
            query.addBindValue(record_id)
            if not query.exec_():
                raise Exception(f"Failed to fetch record: {query.lastError().text()}")

            if not query.next():
                raise Exception("Record not found")

            old_audio_file = query.value(0)
            old_question = query.value(1)
            old_response = query.value(2)
            custom_audio = query.value(3)

            if new_audio_file != old_audio_file:
                save_dir = "assets/audio/"
                os.makedirs(save_dir, exist_ok=True)
                file_name = os.path.basename(new_audio_file)
                save_path = os.path.join(save_dir, file_name)
                try:
                    with open(new_audio_file, "rb") as src, open(
                        save_path, "wb"
                    ) as dst:
                        dst.write(src.read())
                except Exception as e:
                    raise Exception(f"Échec de la sauvegarde du nouvel audio : {e}")
                new_audio_file = save_path
                custom_audio = 1  # Marquer comme audio personnalisé

            # Vérifier si l'audio doit être régénéré
            if custom_audio != 1 and (
                new_response != old_response or new_question != old_question
            ):
                new_audio_file = self.auto_generate_audio(new_question, new_response)
                if os.path.exists(old_audio_file):
                    try:
                        os.remove(old_audio_file)  # Supprimer l'ancien fichier audio
                    except Exception as e:
                        raise Exception(
                            f"Échec de la suppression de l'ancien audio : {e}"
                        )

            # Sauvegarder le nouveau fichier audio si différent

            # Mettre à jour l'entrée
            query.prepare(
                """
                UPDATE records
                SET audio_file = ?, question = ?, response = ?, custom_audio = ?
                WHERE UUID = ?
                """
            )
            query.addBindValue(new_audio_file)
            query.addBindValue(new_question)
            query.addBindValue(new_response)
            query.addBindValue(custom_audio)
            query.addBindValue(record_id)
            if not query.exec_():
                raise Exception(f"Failed to update record: {query.lastError().text()}")
            return True
        except Exception as e:
            QMessageBox.critical(None, "Erreur", str(e))
            return False

    def delete_record(self, record_id: str) -> bool:
        try:
            """Supprime un entrée de la base de données."""
            query = QSqlQuery(self.db)  # Associer la requête à la connexion nommée
            query.prepare("DELETE FROM records WHERE UUID = ?")
            query.addBindValue(record_id)
            if not query.exec_():
                raise Exception(f"Failed to delete record: {query.lastError().text()}")
            self.db.commit()  # Valider les modifications
            return True
        except Exception as e:
            QMessageBox.critical(None, "Erreur", str(e))
            return False

    def close_connection(self):
        """Ferme la connexion à la base de données."""
        if self.db.isOpen():
            self.db.close()  # Fermer la connexion
        # Nettoyer explicitement les requêtes actives
        QSqlQuery(self.db).clear()
        if QSqlDatabase.contains(self.connection_name):
            try:
                QSqlDatabase.removeDatabase(
                    self.connection_name
                )  # Supprimer la connexion
            except RuntimeError as e:
                print(f"Erreur lors de la suppression de la connexion : {e}")
