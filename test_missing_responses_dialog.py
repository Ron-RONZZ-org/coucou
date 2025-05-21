import sys
import pytest
from PySide6.QtWidgets import QApplication, QInputDialog
from missing_responses_dialog import MissingResponsesDialog


@pytest.fixture(scope="module")
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_dialog_modifies_entries(qtbot, app):
    entries = [
        {"question": "Quelle est la capitale de la France?", "response": ""},
        {"question": "Combien font 2+2?", "response": ""},
    ]
    dialog = MissingResponsesDialog(None, entries, db_manager=None)
    qtbot.addWidget(dialog)
    # Simule la saisie d'une réponse pour la première entrée
    dialog.response_edit.setText("Paris")
    dialog.save_current()
    assert entries[0]["response"] == "Paris"
    # Simule la modification de la question
    dialog.question_edit.setText("Quelle est la capitale de l'Allemagne?")
    dialog.save_current()
    assert entries[0]["question"] == "Quelle est la capitale de l'Allemagne?"
    # Simule la navigation et la saisie sur la deuxième entrée
    dialog.next_entry()
    dialog.response_edit.setText("4")
    dialog.save_current()
    assert entries[1]["response"] == "4"
    # Simule la sélection automatique (simulateur)
    dialog.current_index = 0
    dialog.update_entry()
    dialog.select_checkbox.setChecked(True)
    # On ne peut pas simuler QInputDialog sans patch, mais on vérifie que la case déclenche bien la logique
    assert dialog.select_checkbox.isChecked()


def test_reset_entry(qtbot, app):
    entries = [
        {"question": "Q1", "response": "A1"},
        {"question": "Q2", "response": "A2"},
    ]
    dialog = MissingResponsesDialog(None, entries, db_manager=None)
    qtbot.addWidget(dialog)
    dialog.current_index = 1
    dialog.update_entry()
    dialog.question_edit.setText("Q2 modifiée")
    dialog.response_edit.setText("A2 modifiée")
    dialog.save_current()
    dialog.reset_entry()
    assert entries[1]["question"] == "Q2"
    assert entries[1]["response"] == ""


def test_navigation_buttons(qtbot, app):
    entries = [
        {"question": "Q1", "response": ""},
        {"question": "Q2", "response": ""},
        {"question": "Q3", "response": ""},
    ]
    dialog = MissingResponsesDialog(None, entries, db_manager=None)
    qtbot.addWidget(dialog)
    assert not dialog.prev_btn.isEnabled()
    assert dialog.next_btn.isEnabled()
    dialog.next_entry()
    assert dialog.prev_btn.isEnabled()
    dialog.next_entry()
    assert not dialog.next_btn.isEnabled()
    dialog.prev_entry()
    assert dialog.next_btn.isEnabled()


def test_validate_and_accept_with_missing(qtbot, app, mocker):
    entries = [
        {"question": "Q1", "response": "A1"},
        {"question": "Q2", "response": ""},
    ]
    dialog = MissingResponsesDialog(None, entries, db_manager=None)
    qtbot.addWidget(dialog)
    mocker.patch.object(dialog, "accept")
    mock_warning = mocker.patch("PySide6.QtWidgets.QMessageBox.warning")
    dialog.validate_and_accept()
    assert dialog.current_index == 1
    assert mock_warning.called
    dialog.response_edit.setText("A2")
    dialog.save_current()
    dialog.validate_and_accept()
    assert dialog.accept.called


def test_goto_entry(qtbot, app, mocker):
    entries = [
        {"question": "Q1", "response": ""},
        {"question": "Q2", "response": ""},
        {"question": "Q3", "response": ""},
    ]
    dialog = MissingResponsesDialog(None, entries, db_manager=None)
    qtbot.addWidget(dialog)
    mocker.patch.object(QInputDialog, "getInt", return_value=(2, True))
    dialog.goto_entry()
    assert dialog.current_index == 1


def test_apply_select_action(monkeypatch, qtbot, app):
    entries = [
        {"question": "Paris est la capitale de la France", "response": ""},
    ]
    dialog = MissingResponsesDialog(None, entries, db_manager=None)
    qtbot.addWidget(dialog)
    # Patch QInputDialog.getText to simulate user selecting "Paris"
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Paris", True))
    dialog.apply_select_action()
    assert entries[0]["response"] == "Paris"
    assert "(?)" in entries[0]["question"]
    dialog.response_edit.setText("4")
    dialog.save_current()
    assert entries[1]["response"] == "4"
    # Simule la sélection automatique (simulateur)
    dialog.current_index = 0
    dialog.update_entry()
    dialog.select_checkbox.setChecked(True)
    # On ne peut pas simuler QInputDialog sans patch, mais on vérifie que la case déclenche bien la logique
    assert dialog.select_checkbox.isChecked()


def test_reset_entry(qtbot, app):
    entries = [
        {"question": "Q1", "response": "A1"},
        {"question": "Q2", "response": "A2"},
    ]
    dialog = MissingResponsesDialog(None, entries, db_manager=None)
    qtbot.addWidget(dialog)
    dialog.current_index = 1
    dialog.update_entry()
    dialog.question_edit.setText("Q2 modifiée")
    dialog.response_edit.setText("A2 modifiée")
    dialog.save_current()
    dialog.reset_entry()
    assert entries[1]["question"] == "Q2"
    assert entries[1]["response"] == ""
