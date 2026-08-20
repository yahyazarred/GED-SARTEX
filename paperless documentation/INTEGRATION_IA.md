# Intégration optionnelle des fonctions IA

## 1. Séparation des responsabilités

Cette section est volontairement séparée du fonctionnement principal. GED-SARTEX/Paperless-ngx fonctionne sans IA. Le stack `paperless-stack` ajoute des services externes qui utilisent l’API Paperless :

- **Ollama** exécute les modèles localement ;
- **Open WebUI** permet de gérer et tester les modèles ;
- **Paperless-AI** suggère ou applique des métadonnées ;
- **Paperless-GPT** améliore l’OCR par vision et peut suggérer des métadonnées ;
- **Dozzle** affiche les journaux Docker.

Flux : document → GED-SARTEX/Paperless-ngx → OCR/index ; puis, facultativement, Paperless-AI/Paperless-GPT consultent l’API, appellent Ollama et écrivent des résultats dans Paperless.

## 2. Point essentiel pour utiliser la version GED-SARTEX

Le dépôt `timothystewart6/paperless-stack` référence l’image officielle :

```yaml
image: ghcr.io/paperless-ngx/paperless-ngx:latest
```

Cette ligne n’inclut pas les armoires, signatures et workflows GED-SARTEX. Il faut la remplacer par une image issue de ce dépôt.

### Option A — construire GED-SARTEX dans le stack

Placer les dépôts côte à côte :

```text
livraison/
├── GED-SARTEX/
└── paperless-stack/
```

Dans le service Paperless du `compose.yaml` du stack :

```yaml
paperless:
  image: ged-sartex/paperless-ngx:local
  build:
    context: ../GED-SARTEX
    dockerfile: Dockerfile
```

Conserver les volumes, ports, `env_file`, `depends_on` et réseaux du stack. Puis :

```bash
cd paperless-stack
docker compose build paperless
docker compose up -d
```

### Option B — utiliser une image publiée

Construire et publier une version immuable :

```bash
cd GED-SARTEX
docker build -t ghcr.io/<organisation>/ged-sartex:1.0.0 .
docker push ghcr.io/<organisation>/ged-sartex:1.0.0
```

Puis remplacer l’image du service Paperless :

```yaml
paperless:
  image: ghcr.io/<organisation>/ged-sartex:1.0.0
```

Ne pas utiliser `latest` en production. Si l’image GHCR est privée, effectuer `docker login ghcr.io` avec un jeton disposant de `read:packages`.

## 3. Prérequis matériels

Le socle Paperless fonctionne sur un serveur modeste. Les modèles locaux changent fortement les besoins :

- modèle texte léger : plusieurs Go de RAM ;
- modèle vision : davantage de RAM/VRAM et temps de traitement ;
- GPU NVIDIA : pilotes et NVIDIA Container Toolkit ;
- sans GPU : fonctionnement possible mais souvent beaucoup plus lent.

Dimensionner après un test représentatif. Ne pas activer automatiquement l’IA sur tout l’historique avant d’avoir mesuré le débit, les erreurs et la qualité.

## 4. Installation du stack IA

```bash
git clone https://github.com/timothystewart6/paperless-stack.git
cd paperless-stack
```

Lire le README et le guide Techno Tim correspondant à la version récupérée. Modifier les mots de passe et secrets dans chaque fichier `.env`, notamment `paperless/.env` et `postgres/.env`. Les identifiants PostgreSQL doivent correspondre des deux côtés.

Avant le démarrage, intégrer l’image GED-SARTEX comme décrit plus haut. Ensuite :

```bash
docker compose config
docker compose up -d
docker compose ps
```

Accès annoncés par le stack de référence :

- GED-SARTEX/Paperless : `http://<serveur>:8000` ;
- Paperless-AI : `http://<serveur>:3000` ;
- Open WebUI : `http://<serveur>:3001` ;
- Paperless-GPT : `http://<serveur>:3002` ;
- Dozzle : `http://<serveur>:8080`.

Ne pas exposer ces ports directement sur Internet. Utiliser VPN, pare-feu et reverse proxy HTTPS.

## 5. Modèles Ollama

Le stack de référence propose notamment `llama3.2:3b` pour les suggestions/raisonnement et `minicpm-v:8b` pour la vision. Les noms doivent correspondre exactement aux variables des fichiers `.env` de Paperless-AI et Paperless-GPT.

Télécharger depuis le conteneur ou Open WebUI selon le stack :

```bash
docker compose exec ollama ollama pull llama3.2:3b
docker compose exec ollama ollama pull minicpm-v:8b
docker compose exec ollama ollama list
```

Les modèles évoluent. Valider la licence, la langue française, la mémoire requise et la qualité avant de changer de modèle.

## 6. Jeton API Paperless

Dans GED-SARTEX/Paperless, ouvrir le profil puis générer un jeton API pour un compte de service dédié. Copier ce jeton dans les configurations de Paperless-AI et Paperless-GPT, ainsi que l’URL interne du service Paperless.

Bonnes pratiques :

- ne pas utiliser le compte superutilisateur ;
- créer un compte de service par intégration si possible ;
- accorder uniquement les permissions nécessaires ;
- protéger les fichiers `.env` ;
- faire tourner le jeton après exposition ou départ d’un administrateur ;
- vérifier que les réponses IA ne contournent pas les permissions de documents.

Après modification :

```bash
docker compose up -d --force-recreate paperless-ai paperless-gpt
docker compose logs -f paperless-ai paperless-gpt
```

## 7. Interaction avec les fonctions GED-SARTEX

Paperless-AI et Paperless-GPT ont été conçus pour l’API Paperless-ngx standard. Ils peuvent généralement proposer titres, correspondants, types et tags. Les **armoires GED-SARTEX** sont une extension : elles ne seront pas automatiquement comprises par ces projets tant que leur code ne prend pas en charge le champ/API d’armoire.

Approche recommandée :

1. laisser l’IA appliquer des tags/correspondants/types compatibles ;
2. utiliser ensuite les algorithmes de correspondance d’armoires ou un workflow GED-SARTEX pour classer le document ;
3. si une intégration directe est souhaitée, adapter le connecteur IA pour lire la liste des armoires et écrire l’identifiant `cabinet` via l’API GED-SARTEX ;
4. ajouter des tests garantissant qu’aucune armoire inaccessible n’est révélée au compte de service.

Les demandes de signature et approbations ne doivent pas être décidées automatiquement par une IA. L’IA peut assister le classement, mais l’acteur humain reste responsable des décisions et signatures.

## 8. Remplacer le Paperless officiel du stack

Le plan initial consistait à développer les fonctions dans Paperless-ngx puis à remplacer le composant Paperless du stack. Techniquement, le stack n’embarque pas le code Paperless dans les services IA : il orchestre une image Paperless et des services séparés. Le remplacement correct est donc limité au service `paperless`/`webserver` :

- conserver PostgreSQL, Redis, Gotenberg, Tika, Ollama, Open WebUI, Paperless-AI, Paperless-GPT et Dozzle ;
- substituer seulement l’image officielle Paperless par l’image GED-SARTEX ;
- conserver les mêmes volumes de données et variables de connexion ;
- appliquer les migrations GED-SARTEX au premier démarrage ;
- régénérer les jetons API si l’instance est neuve ;
- réaliser une recette complète des fonctions GED-SARTEX et IA.

Ne pas copier le dossier source dans le conteneur officiel en cours d’exécution. Une image reconstruite est nécessaire car le frontend Angular et les dépendances backend doivent être compilés ensemble.

## 9. Sécurité et confidentialité de l’IA

Même locale, l’IA augmente la surface d’attaque et traite potentiellement le contenu complet des documents. Avant activation :

- confirmer que les modèles et images ne contactent aucun service cloud non prévu ;
- isoler le réseau Docker et ne publier que les ports nécessaires ;
- protéger Open WebUI et Dozzle ;
- limiter le compte API aux documents autorisés ;
- journaliser les modifications automatiques ;
- exiger une validation humaine pour les métadonnées critiques ;
- définir la politique de conservation des prompts, caches et journaux ;
- inclure les volumes Ollama/Open WebUI/Paperless-AI/Paperless-GPT dans l’analyse de sauvegarde et de confidentialité.

Une hallucination peut produire un mauvais titre, tag, correspondant ou classement. L’IA ne doit pas être considérée comme une source fiable sans contrôle.

## 10. Désactiver l’IA

Le socle GED-SARTEX reste autonome. Pour retirer l’IA, arrêter et supprimer du Compose les services `open-webui`, `ollama`, `paperless-ai` et `paperless-gpt`, puis supprimer leurs dépendances. Conserver Paperless, PostgreSQL, Redis/Valkey, Gotenberg et Tika.

```bash
docker compose stop paperless-ai paperless-gpt open-webui ollama
```

Ne supprimer les volumes IA qu’après sauvegarde et validation, car cette opération est irréversible.

## 11. Recette IA

1. confirmer que GED-SARTEX affiche ses armoires, signatures et workflows ;
2. vérifier les modèles avec `ollama list` ;
3. tester Paperless-AI sur un document non sensible ;
4. tester Paperless-GPT sur un scan difficile ;
5. vérifier les métadonnées écrites et l’historique ;
6. confirmer qu’un compte API limité ne lit pas un document interdit ;
7. vérifier que l’IA ne déclenche pas involontairement un workflow destructif ;
8. mesurer temps, RAM, VRAM et espace disque ;
9. couper l’accès réseau externe et répéter le test si le fonctionnement local intégral est exigé ;
10. documenter les modèles, versions d’images et paramètres retenus.

## 12. Sources

- Stack Docker : https://github.com/timothystewart6/paperless-stack
- Guide détaillé : https://technotim.com/posts/paperless-ngx-local-ai/
- Paperless-AI : https://github.com/clusterzx/paperless-ai
- Paperless-GPT : https://github.com/icereed/paperless-gpt
- Ollama : https://github.com/ollama/ollama
- Open WebUI : https://github.com/open-webui/open-webui
- Paperless-ngx : https://github.com/paperless-ngx/paperless-ngx
