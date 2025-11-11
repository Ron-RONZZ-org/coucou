#!/bin/bash
# Coucou Build Script for Debian/Linux
# This script automates the compilation process

set -e

echo "================================================"
echo "  Coucou - Script de compilation Debian/Linux"
echo "================================================"
echo ""

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérifier Python 3.12
log_info "Vérification de Python 3.12..."
if ! command -v python3.12 &> /dev/null; then
    log_error "Python 3.12 n'est pas installé"
    echo "Installez Python 3.12 avec:"
    echo "  sudo add-apt-repository ppa:deadsnakes/ppa"
    echo "  sudo apt update"
    echo "  sudo apt install python3.12 python3.12-venv python3.12-dev"
    exit 1
fi

PYTHON_VERSION=$(python3.12 --version | cut -d' ' -f2)
log_info "Python version: $PYTHON_VERSION"

# Vérifier les dépendances système
log_info "Vérification des dépendances système..."
MISSING_DEPS=()

for cmd in git ffmpeg; do
    if ! command -v $cmd &> /dev/null; then
        MISSING_DEPS+=($cmd)
    fi
done

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    log_warn "Dépendances système manquantes: ${MISSING_DEPS[*]}"
    echo "Installez-les avec:"
    echo "  sudo apt install -y ${MISSING_DEPS[*]}"
    read -p "Continuer quand même? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Créer et activer l'environnement virtuel
log_info "Création de l'environnement virtuel..."
if [ ! -d "venv" ]; then
    python3.12 -m venv venv
else
    log_warn "L'environnement virtuel existe déjà"
fi

source venv/bin/activate

# Mettre à jour pip
log_info "Mise à jour de pip..."
pip install --upgrade pip --quiet

# Installer PyInstaller
log_info "Installation de PyInstaller..."
pip install pyinstaller --quiet

# Installer les dépendances du projet
log_info "Installation des dépendances du projet..."
if [ -f "poetry.lock" ]; then
    log_info "Utilisation de Poetry..."
    pip install poetry --quiet
    poetry install
else
    log_info "Installation directe avec pip..."
    # Installer numpy d'abord pour éviter les problèmes de compatibilité
    pip install numpy==1.26.0 --quiet
    pip install scikit-learn==1.3.0 --quiet
    
    # Installer les autres dépendances
    pip install pyside6>=6.9.0 gtts>=2.5.4 mlconjug3>=3.11.0 \
        setuptools>=80.3.1 pyyaml>=6.0.2 joblib>=1.5.0 \
        defusedxml>=0.7.1 Click>=8.0.3 pytest \
        rich toml pydub --quiet
fi

log_info "Dépendances installées avec succès"

# Nettoyer les anciennes compilations
log_info "Nettoyage des anciennes compilations..."
rm -rf build dist/__pycache__

# Compiler avec PyInstaller
log_info "Compilation en cours avec PyInstaller..."
log_info "Cela peut prendre quelques minutes..."

if [ -f "coucou.spec" ]; then
    log_info "Utilisation du fichier coucou.spec existant"
    pyinstaller coucou.spec --clean --noconfirm
else
    log_warn "Fichier coucou.spec non trouvé, utilisation de la commande directe"
    pyinstaller --onedir --windowed \
        --add-data "assets:assets" \
        --add-data "config.toml:." \
        --add-data "template.csv:." \
        --hidden-import PySide6.QtCore \
        --hidden-import PySide6.QtGui \
        --hidden-import PySide6.QtWidgets \
        --hidden-import PySide6.QtMultimedia \
        --hidden-import PySide6.QtSql \
        --hidden-import gtts \
        --hidden-import mlconjug3 \
        --hidden-import sklearn \
        --hidden-import numpy \
        --name coucou \
        --clean \
        main.py
fi

# Vérifier que la compilation a réussi
if [ ! -f "dist/coucou/coucou" ]; then
    log_error "La compilation a échoué - le binaire n'a pas été créé"
    exit 1
fi

# Afficher les informations sur le binaire
log_info "Compilation terminée avec succès!"
echo ""
echo "================================================"
echo "  Informations sur le binaire compilé"
echo "================================================"
echo ""
BINARY_SIZE=$(du -sh dist/coucou | cut -f1)
log_info "Emplacement: ./dist/coucou/coucou"
log_info "Taille totale: $BINARY_SIZE"
echo ""

# Proposer de tester le binaire
read -p "Voulez-vous tester le binaire maintenant? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Lancement de Coucou..."
    ./dist/coucou/coucou &
    sleep 2
    log_info "Coucou devrait maintenant être ouvert"
fi

# Proposer de créer une archive
echo ""
read -p "Voulez-vous créer une archive tar.gz pour distribution? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ARCHIVE_NAME="coucou-linux-x86_64-$(date +%Y%m%d).tar.gz"
    log_info "Création de l'archive: $ARCHIVE_NAME"
    cd dist
    tar -czf "../$ARCHIVE_NAME" coucou/
    cd ..
    ARCHIVE_SIZE=$(du -sh "$ARCHIVE_NAME" | cut -f1)
    log_info "Archive créée: $ARCHIVE_NAME ($ARCHIVE_SIZE)"
fi

echo ""
echo "================================================"
echo "  Prochaines étapes"
echo "================================================"
echo ""
echo "1. Tester le binaire:"
echo "   ./dist/coucou/coucou"
echo ""
echo "2. Créer une entrée de bureau (.desktop):"
echo "   Voir Debian-Linux-Compile.md pour les instructions"
echo ""
echo "3. Distribuer le binaire:"
echo "   Le dossier dist/coucou/ contient tout le nécessaire"
echo ""
log_info "Pour plus d'informations, consultez Debian-Linux-Compile.md"
echo ""
