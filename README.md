> ❗ Coucou currently only supports French. Support for other languages will follow in about a week.

Coucou is a multi-platform minimalist FOSS wordbank for language learning.

- Main functionalities
    - Import `.csv` vocabulary list and audio files
    - Automatically generate audio with Google TTS
    - Review a custom range of saved vocabularies
        - filter by date
    - Export and restore progress of a review session
    - Search for and edit saved vocabulaires

- Advantages
    - Run anywhere
        - Coucou is based on PySide 6, and can therefore be compiled to run on desktop (Linux family systems, Windows, macOS) and mobile platforms (Ubuntu Touch, Android, iOS)
    - Minimalist interface
        - Coucou's minimalist interface directs your attention to the language you are trying to learn.
- Project status
    - Alpha
        - ✅All main functionalities work.
        - ❗No build version yet. Running from python source code is adequately fast and resource efficient, even on very low-spec machines (2GB RAM).
    - To do
        - Language support (English planned, contributions on other languages welcome)
        - slightly prettier UI design
        - Add a French conjugator (conjugateur pour les verbes français).
- Development
    - Known problem : mlconjug3 requires scikit-learn 1.3.0, which in term requires numpy 1.25, which is incompatible with python 3.12.
        - the good news is scikit-learn 1.3.0 works just fine with numpy 1.26.0 in reality
        - the bad news is the inaccurate dependence requirements of scikit-learn 1.3.0 ruins Pip/Poetry's effort to resolve dependencies.
        - a fix requires significant effort from the package maintainers and is not happening anytime soon, since the scikit-learn 1.3.0 version is severely out of date, while mlconjug3 is no longer actively updated (who wants to continue to work on a perfectly functional package just because some stupid people decided to break backward compability).
        - Therefore we have to duct tape our way out with `numpy (==1.26.0)`, overwriting internal dependence of scikit-learn 1.3.0
      