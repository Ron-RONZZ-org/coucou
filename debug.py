import debugpy

# Configure le port pour le débogueur
debugpy.listen(("localhost", 5678))
print("Le débogueur est prêt et attend une connexion sur le port 5678.")

# Attendre que le client de débogage se connecte
debugpy.wait_for_client()

# Importer et exécuter votre application principale
import main

main.main()
