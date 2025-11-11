# Coucou - Instructions de compilation pour Debian/Linux

Ce guide fournit des instructions détaillées pour compiler Coucou en un binaire autonome sur les systèmes Debian et dérivés (Ubuntu, Linux Mint, etc.).

## Table des matières

1. [Prérequis système](#prérequis-système)
2. [Installation des dépendances](#installation-des-dépendances)
3. [Méthode 1 : Compilation avec PyInstaller (Recommandée)](#méthode-1--compilation-avec-pyinstaller-recommandée)
4. [Méthode 2 : Compilation avec Nuitka (Alternative)](#méthode-2--compilation-avec-nuitka-alternative)
5. [Création d'une entrée de bureau (.desktop)](#création-dune-entrée-de-bureau-desktop)
6. [Tests post-compilation](#tests-post-compilation)
7. [Dépannage](#dépannage)

---

## Prérequis système

### Configuration minimale
- **OS** : Debian 11+ (Bullseye) ou dérivés (Ubuntu 22.04+, Linux Mint 21+)
- **RAM** : 2 GB minimum (4 GB recommandés pour la compilation)
- **Espace disque** : 500 MB pour les dépendances + 200 MB pour le binaire compilé
- **Python** : Version 3.12 (obligatoire, pas 3.13)

### Vérifier votre version de Python

```bash
python3 --version
```

Si vous n'avez pas Python 3.12, installez-le :

```bash
# Sur Ubuntu/Debian
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev
```

---

## Installation des dépendances

### 1. Paquets système requis

```bash
sudo apt update
sudo apt install -y \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-pip \
    git \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libdbus-1-3 \
    libxkbcommon-x11-0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-xinerama0 \
    libxcb-xfixes0 \
    libxcb-cursor0 \
    libegl1 \
    libfontconfig1 \
    libxrender1 \
    libxi6 \
    libxext6 \
    libx11-xcb1 \
    ffmpeg
```

### 2. Cloner le dépôt (si ce n'est pas déjà fait)

```bash
git clone https://github.com/Ron-RONZZ-org/coucou.git
cd coucou
```

### 3. Créer un environnement virtuel

```bash
python3.12 -m venv venv
source venv/bin/activate
```

### 4. Installer Poetry (optionnel mais recommandé)

```bash
pip install poetry
poetry install
```

**OU** installer directement avec pip :

```bash
pip install --upgrade pip
pip install pyside6>=6.9.0 gtts>=2.5.4 mlconjug3>=3.11.0 \
    setuptools>=80.3.1 pyyaml>=6.0.2 joblib>=1.5.0 \
    defusedxml>=0.7.1 Click>=8.0.3 pytest \
    scikit-learn==1.3.0 numpy==1.26.0 rich toml pydub
```

**Note importante** : L'ordre des dépendances est important. `numpy==1.26.0` doit être installé pour contourner les problèmes de compatibilité avec scikit-learn 1.3.0.

---

## Méthode 1 : Compilation avec PyInstaller (Recommandée)

PyInstaller est l'outil recommandé pour compiler Coucou en un binaire autonome.

### 1. Installer PyInstaller

```bash
pip install pyinstaller
```

### 2. Créer le fichier de spécification

Créez un fichier `coucou.spec` à la racine du projet :

```bash
cat > coucou.spec << 'EOF'
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('config.toml', '.'),
        ('template.csv', '.'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtMultimedia',
        'PySide6.QtSql',
        'gtts',
        'mlconjug3',
        'sklearn',
        'numpy',
        'yaml',
        'toml',
        'pydub',
        'rich',
        'defusedxml',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'tkinter',
        'PIL',
        'cv2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='coucou',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='coucou',
)
EOF
```

### 3. Compiler avec PyInstaller

```bash
pyinstaller coucou.spec --clean
```

Le binaire compilé se trouvera dans `dist/coucou/`.

### 4. Tester le binaire

```bash
./dist/coucou/coucou
```

### 5. (Optionnel) Créer une version "one-file"

Pour un seul fichier exécutable (plus lent au démarrage) :

```bash
pyinstaller --onefile --windowed \
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
    --name coucou \
    main.py
```

---

## Méthode 2 : Compilation avec Nuitka (Alternative)

Nuitka produit un binaire plus performant mais la compilation est plus longue.

### 1. Installer Nuitka

```bash
pip install nuitka
sudo apt install -y patchelf ccache
```

### 2. Compiler avec Nuitka

```bash
python3.12 -m nuitka \
    --standalone \
    --enable-plugin=pyside6 \
    --include-data-dir=assets=assets \
    --include-data-file=config.toml=config.toml \
    --include-data-file=template.csv=template.csv \
    --follow-imports \
    --assume-yes-for-downloads \
    --disable-console \
    --output-dir=build_nuitka \
    --output-filename=coucou \
    main.py
```

**Note** : La compilation avec Nuitka peut prendre 10-30 minutes selon votre matériel.

### 3. Le binaire se trouve dans

```bash
./build_nuitka/main.dist/coucou
```

---

## Création d'une entrée de bureau (.desktop)

Pour ajouter Coucou au menu des applications :

### 1. Créer le fichier .desktop

```bash
cat > ~/.local/share/applications/coucou.desktop << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=Coucou
Comment=Application de banque de mots pour l'apprentissage des langues
Exec=/chemin/vers/coucou/dist/coucou/coucou
Icon=/chemin/vers/coucou/assets/icon.png
Terminal=false
Categories=Education;Languages;
Keywords=language;learning;vocabulary;french;
EOF
```

**Important** : Remplacez `/chemin/vers/coucou/` par le chemin absolu vers votre installation.

### 2. Créer une icône (si elle n'existe pas)

Si vous n'avez pas d'icône, vous pouvez utiliser une icône générique ou créer la vôtre :

```bash
# Option 1 : Utiliser une icône système
Icon=applications-education

# Option 2 : Créer/placer votre propre icône
# Placez votre icône dans assets/icon.png
```

### 3. Rendre le fichier .desktop exécutable

```bash
chmod +x ~/.local/share/applications/coucou.desktop
```

### 4. Actualiser le cache des applications

```bash
update-desktop-database ~/.local/share/applications/
```

---

## Tests post-compilation

### Tests de base

1. **Lancement de l'application** :
   ```bash
   ./dist/coucou/coucou
   ```

2. **Vérifier le chargement de la base de données** :
   - L'application devrait démarrer avec le splash screen
   - Vérifier que les boutons principaux sont visibles

3. **Test d'importation CSV** :
   - Cliquer sur "Importer vocabulaires"
   - Importer le fichier `template.csv`

4. **Test de génération audio** :
   - Vérifier que gTTS fonctionne
   - Les fichiers audio devraient être créés dans `assets/audio/`

5. **Test de révision** :
   - Cliquer sur "Réviser"
   - Vérifier que les vocabulaires importés sont affichés

### Tests avancés

```bash
# Vérifier les dépendances du binaire
ldd ./dist/coucou/coucou

# Vérifier la taille du binaire
du -sh ./dist/coucou/

# Tester sur un système propre (sans Python installé)
# Copier le dossier dist/coucou/ sur une autre machine et tester
```

---

## Dépannage

### Problème : "ImportError: No module named..."

**Solution** : Ajoutez le module manquant dans `hiddenimports` du fichier `.spec` :

```python
hiddenimports=[
    # ... autres imports
    'votre_module_manquant',
]
```

Puis recompilez.

### Problème : "Qt platform plugin could not be initialized"

**Solution** : Installez les bibliothèques Qt manquantes :

```bash
sudo apt install -y libxcb-cursor0 libxcb-xinerama0
```

### Problème : Audio ne fonctionne pas

**Solution** : Vérifiez que FFmpeg est installé :

```bash
sudo apt install -y ffmpeg
ffmpeg -version
```

### Problème : "libpython3.12.so.1.0: cannot open shared object file"

**Solution** : Installez les bibliothèques Python de développement :

```bash
sudo apt install -y python3.12-dev
```

### Problème : Le binaire est trop gros (>300 MB)

**Solutions** :
1. Excluez les modules inutiles dans le `.spec`
2. Utilisez UPX pour compresser (déjà activé par défaut)
3. Utilisez la méthode "onefile" (mais démarrage plus lent)

### Problème : numpy/scikit-learn ne s'installent pas

**Solution** : Installez dans l'ordre exact :

```bash
pip install numpy==1.26.0
pip install scikit-learn==1.3.0
pip install mlconjug3>=3.11.0
```

### Problème : La compilation échoue avec "Memory Error"

**Solution** : 
1. Fermez les applications inutiles
2. Ajoutez de la swap :
   ```bash
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

### Problème : Permission denied lors de l'exécution

**Solution** :

```bash
chmod +x ./dist/coucou/coucou
```

---

## Distribution du binaire

### Créer une archive pour distribution

```bash
cd dist
tar -czf coucou-linux-x86_64.tar.gz coucou/
```

### Créer un package Debian (.deb)

Pour créer un package .deb installable :

1. Installer les outils nécessaires :
   ```bash
   sudo apt install -y dpkg-dev debhelper
   ```

2. Créer la structure du package :
   ```bash
   mkdir -p coucou-deb/DEBIAN
   mkdir -p coucou-deb/usr/local/bin
   mkdir -p coucou-deb/usr/share/applications
   mkdir -p coucou-deb/usr/share/icons/hicolor/256x256/apps
   ```

3. Copier les fichiers :
   ```bash
   cp -r dist/coucou/* coucou-deb/usr/local/bin/
   cp coucou.desktop coucou-deb/usr/share/applications/
   # cp icon.png coucou-deb/usr/share/icons/hicolor/256x256/apps/coucou.png
   ```

4. Créer le fichier de contrôle :
   ```bash
   cat > coucou-deb/DEBIAN/control << 'EOF'
   Package: coucou
   Version: 0.1.0
   Section: education
   Priority: optional
   Architecture: amd64
   Maintainer: Ron Chou <ron@ronzz.org>
   Description: Application de banque de mots pour l'apprentissage des langues
    Coucou est une application minimaliste et multiplateforme FOSS
    pour l'apprentissage des langues, avec support pour l'import de
    vocabulaire, génération audio TTS, et révision espacée.
   Depends: libgl1-mesa-glx, libglib2.0-0, libdbus-1-3, ffmpeg
   EOF
   ```

5. Construire le package :
   ```bash
   dpkg-deb --build coucou-deb
   mv coucou-deb.deb coucou_0.1.0_amd64.deb
   ```

6. Installer le package :
   ```bash
   sudo dpkg -i coucou_0.1.0_amd64.deb
   sudo apt-get install -f  # Résoudre les dépendances manquantes
   ```

---

## Automatisation avec un script

Créez un script `build.sh` pour automatiser la compilation :

```bash
#!/bin/bash
set -e

echo "=== Compilation de Coucou pour Debian/Linux ==="

# Vérifier Python 3.12
if ! python3.12 --version &> /dev/null; then
    echo "Erreur: Python 3.12 n'est pas installé"
    exit 1
fi

# Créer et activer l'environnement virtuel
echo "Création de l'environnement virtuel..."
python3.12 -m venv venv
source venv/bin/activate

# Installer les dépendances
echo "Installation des dépendances..."
pip install --upgrade pip
pip install pyinstaller

if [ -f "poetry.lock" ]; then
    pip install poetry
    poetry install
else
    pip install -r requirements.txt 2>/dev/null || \
    pip install pyside6>=6.9.0 gtts>=2.5.4 mlconjug3>=3.11.0 \
        setuptools>=80.3.1 pyyaml>=6.0.2 joblib>=1.5.0 \
        defusedxml>=0.7.1 Click>=8.0.3 pytest \
        scikit-learn==1.3.0 numpy==1.26.0 rich toml pydub
fi

# Nettoyer les anciennes compilations
echo "Nettoyage..."
rm -rf build dist *.spec

# Compiler
echo "Compilation avec PyInstaller..."
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
    --name coucou \
    main.py

echo "=== Compilation terminée ==="
echo "Binaire disponible dans: ./dist/coucou/coucou"
echo ""
echo "Pour tester: ./dist/coucou/coucou"
```

Rendre le script exécutable :

```bash
chmod +x build.sh
./build.sh
```

---

## Ressources supplémentaires

- **PyInstaller Documentation** : https://pyinstaller.org/
- **Nuitka Documentation** : https://nuitka.net/
- **PySide6 Documentation** : https://doc.qt.io/qtforpython/
- **Projet Coucou** : https://github.com/Ron-RONZZ-org/coucou

---

## Licence

Coucou est distribué sous licence AGPL 3.0. Voir le fichier LICENSE pour plus de détails.

---

**Dernière mise à jour** : Novembre 2024

Pour toute question ou problème, veuillez ouvrir une issue sur GitHub : https://github.com/Ron-RONZZ-org/coucou/issues
