# GED-SARTEX — dossier de livraison

Cette branche contient une version personnalisée de Paperless-ngx comprenant les armoires, la signature visuelle et les workflows séquentiels avec approbations. La documentation de transfert est organisée comme suit :

- `documentation/GUIDE_INSTALLATION.md` : installation Docker Compose, exécution de développement, configuration, sauvegarde, mise à jour et dépannage ;
- `documentation/GUIDE_UTILISATEUR.md` : utilisation détaillée de Paperless-ngx et des fonctions GED-SARTEX ;
- `documentation/INTEGRATION_IA.md` : ajout optionnel de Paperless-AI, Paperless-GPT, Ollama et Open WebUI ;
- `deployment/docker-compose.yml` : déploiement autonome construit depuis ce dépôt ;
- `deployment/.env.example` et `deployment/paperless.env.example` : modèles de configuration sans secret.

Le manuel Word consolidé est généré dans `livrables/Manuel_GED_SARTEX.docx`.

## Démarrage rapide

Depuis la racine du dépôt :

```bash
cd deployment
cp .env.example .env
cp paperless.env.example paperless.env
```

Remplacer les valeurs `REMPLACER_...`, puis :

```bash
mkdir -p consume export
docker compose build webserver
docker compose up -d
docker compose exec webserver createsuperuser
```

Ouvrir `http://localhost:8000`.

> Ne jamais utiliser les valeurs d’exemple en production. Lire entièrement le guide d’installation avant une mise en service réelle.
