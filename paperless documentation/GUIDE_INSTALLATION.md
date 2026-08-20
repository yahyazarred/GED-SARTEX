# Guide d’installation, d’exploitation et de transfert — GED-SARTEX

## 1. Objet et périmètre

GED-SARTEX est une dérivation de Paperless-ngx. Elle conserve le socle de gestion documentaire (import, OCR, recherche, tags, correspondants, types, stockage, permissions, API et tâches asynchrones) et ajoute :

- les **armoires** avec classement, recherche, correspondance automatique et héritage facultatif des permissions ;
- la **signature visuelle** avec groupe intégré de signataires, demandes ciblées, parapheur, placement de signature et copies signées distinctes des versions ordinaires ;
- les **workflows séquentiels** avec déclencheur initial, actions ordonnées, approbations humaines, demandes de signature, correspondance automatique, branches de rejet et suivi détaillé ;
- les libellés français des écrans ajoutés.

Cette signature est visuelle et fonctionnelle. Elle ne constitue pas, à elle seule, une signature électronique qualifiée ou un dispositif de preuve conforme à eIDAS. Toute exigence juridique doit faire l’objet d’une étude séparée.

## 2. Dépôts et ressources

- Version GED-SARTEX : https://github.com/yahyazarred/GED-SARTEX
- Projet amont Paperless-ngx : https://github.com/paperless-ngx/paperless-ngx
- Documentation amont : https://docs.paperless-ngx.com/
- Stack IA de référence : https://github.com/timothystewart6/paperless-stack
- Guide du stack IA : https://technotim.com/posts/paperless-ngx-local-ai/
- Démonstration vidéo fournie : https://youtu.be/NMAwHjleqHg

La documentation amont reste la référence pour les fonctions Paperless-ngx non modifiées. Le présent guide prévaut pour la construction et le fonctionnement des ajouts GED-SARTEX.

## 3. Recommandation de déploiement

Pour une recette ou une production, utiliser Docker Compose avec PostgreSQL. Cette méthode isole les dépendances, construit exactement le code livré, lance les migrations au démarrage et facilite les sauvegardes. L’exécution « normale » sans Docker doit être réservée au développement.

Architecture du Compose fourni :

- `webserver` : image GED-SARTEX construite depuis le `Dockerfile` du dépôt ;
- `db` : PostgreSQL 18, stockage des métadonnées, permissions, workflows, demandes et états ;
- `broker` : Valkey, file d’attente, cache et communication asynchrone ;
- `gotenberg` et `tika` : conversion et extraction de documents bureautiques ;
- volumes `data`, `media`, `pgdata`, `redisdata` : données persistantes ;
- répertoires `deployment/consume` et `deployment/export` : échanges avec l’hôte.

Les signatures déposées et les PDF signés sont conservés dans le volume `media`. Les armoires, permissions et activités de workflow sont en base PostgreSQL. Une sauvegarde limitée à un seul de ces emplacements est donc incomplète.

## 4. Prérequis Docker

- Linux 64 bits recommandé, ou Windows/macOS avec Docker Desktop ;
- Docker Engine récent avec le module `docker compose` ;
- Git ;
- au moins 4 Go de RAM pour le socle, davantage selon le volume et l’OCR ;
- espace disque dimensionné pour les originaux, archives OCR, miniatures, signatures, copies signées et sauvegardes ;
- accès aux registres Docker, GitHub et dépôts de paquets pendant la première construction.

Pour une exploitation d’entreprise, prévoir un nom DNS, TLS via un reverse proxy, une stratégie de sauvegarde hors machine et une supervision.

## 5. Installation Docker Compose depuis le dépôt

### 5.1 Récupérer une version immuable

Éviter de déployer directement un état mouvant de `main`. Utiliser un tag de livraison :

```bash
git clone https://github.com/yahyazarred/GED-SARTEX.git
cd GED-SARTEX
git fetch --tags
git checkout <TAG_DE_LIVRAISON>
```

Si aucun tag n’a encore été créé, noter le hash exact :

```bash
git rev-parse HEAD
```

### 5.2 Préparer les fichiers de configuration

```bash
cd deployment
cp .env.example .env
cp paperless.env.example paperless.env
mkdir -p consume export
```

Générer les secrets sur une machine disposant de Python :

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Placer la première valeur dans `PAPERLESS_SECRET_KEY` de `paperless.env` et la seconde dans `POSTGRES_PASSWORD` de `.env`. Ces fichiers ne doivent jamais être commités, transmis par messagerie non sécurisée ou publiés.

Vérifier au minimum :

- `PAPERLESS_TIME_ZONE=Europe/Paris` ;
- `PAPERLESS_OCR_LANGUAGE=fra` si les documents sont majoritairement français ;
- `PAPERLESS_OCR_LANGUAGES=fra eng` si les deux langues doivent être reconnues ;
- `PAPERLESS_PORT=8000`, ou un port hôte libre ;
- `USERMAP_UID` et `USERMAP_GID` si les dossiers liés nécessitent un alignement de permissions Linux.

### 5.3 Valider et construire

```bash
docker compose config
docker compose build webserver
docker compose up -d
docker compose ps
```

Le premier build peut être long : il installe les dépendances frontend, compile Angular, installe les dépendances Python et prépare l’image. Les démarrages suivants réutilisent le cache.

Suivre le démarrage :

```bash
docker compose logs -f webserver
```

Attendre que le service soit sain, puis créer l’administrateur :

```bash
docker compose exec webserver createsuperuser
```

Ouvrir `http://<serveur>:8000`.

### 5.4 Contrôles de recette immédiats

Après la première connexion :

1. vérifier la présence de **Documents**, **Armoires**, **Demandes de signature/Parapheur**, **Approbation**, **Workflows** et **Activité des workflows** selon les permissions du compte ;
2. créer une armoire de test et lui affecter un document ;
3. créer un utilisateur signataire, l’ajouter au groupe intégré des signataires et lui accorder la consultation du document ;
4. déposer une signature, demander une signature et produire une copie signée ;
5. créer un workflow simple « document ajouté → affectation d’un tag » ;
6. créer un workflow avec approbation, puis vérifier son activité ;
7. passer l’interface en français et recharger la page ;
8. vérifier l’import OCR d’un PDF et, si nécessaire, d’un fichier Office.

Ne pas accepter la recette si les migrations échouent, si les tâches restent indéfiniment en attente ou si les permissions exposent un document/copie signée à un utilisateur non autorisé.

## 6. Publication d’une image réutilisable

Construire sur chaque serveur fonctionne, mais publier une image versionnée rend la livraison reproductible :

```bash
docker build -t ghcr.io/<organisation>/ged-sartex:1.0.0 .
docker push ghcr.io/<organisation>/ged-sartex:1.0.0
```

Dans `deployment/.env` :

```dotenv
GED_SARTEX_IMAGE=ghcr.io/<organisation>/ged-sartex:1.0.0
```

Le bloc `build` peut rester présent : `docker compose up` utilisera l’image locale si elle existe, tandis que `docker compose build` permet une reconstruction. Pour une exploitation strictement contrôlée, créer un Compose de production ne contenant que `image:` avec un tag immuable ou un digest SHA256.

## 7. Configuration d’un domaine et de HTTPS

Ne pas exposer directement le port 8000 sur Internet. Placer l’application derrière Caddy, Traefik ou Nginx avec un certificat TLS. Configurer dans `paperless.env` :

```dotenv
PAPERLESS_URL=https://ged.example.com
PAPERLESS_ALLOWED_HOSTS=ged.example.com
PAPERLESS_CSRF_TRUSTED_ORIGINS=https://ged.example.com
```

Limiter le port à l’interface locale si le reverse proxy est sur la même machine. Protéger les interfaces administratives et IA par VPN ou contrôle d’accès. Vérifier que le proxy transmet les en-têtes usuels et autorise les WebSockets ; ceux-ci alimentent notamment les mises à jour d’état en temps réel.

## 8. Exécution en environnement de développement

### 8.1 Dev Container recommandé

Prérequis : VS Code, extension **Dev Containers**, Docker Desktop/Engine.

1. ouvrir la racine `GED-SARTEX` dans VS Code ;
2. exécuter **Dev Containers: Reopen in Container** ;
3. utiliser la configuration déjà présente dans `.devcontainer` — ne pas créer un nouveau modèle Alpine/Anaconda ;
4. attendre `uv sync --python 3.13 --group dev` ;
5. dans le terminal du conteneur :

```bash
cd /usr/src/paperless/paperless-ngx
export PAPERLESS_SECRET_KEY="${PAPERLESS_SECRET_KEY:-$(uv run python -c 'import secrets; print(secrets.token_urlsafe(64))')}"
uv run python src/manage.py migrate
```

Compiler le frontend servi sur le port 8000 :

```bash
cd src-ui
pnpm install
pnpm exec ng build --configuration production --localize
cd ..
```

Lancer l’ASGI et le worker dans deux terminaux :

```bash
uv run daphne -b 0.0.0.0 -p 8000 paperless.asgi:application
```

```bash
uv run celery --app paperless worker -l INFO
```

Le service Redis, Tika et Gotenberg provient du Compose du Dev Container. Daphne est préférable au simple `runserver` pour vérifier le comportement WebSocket. Ouvrir `http://localhost:8000`.

En cas d’erreur du paquet Autobahn sous Python 3.14, rester sur Python 3.13 comme la configuration fournie et conserver `UV_NO_BINARY_PACKAGE=autobahn`.

### 8.2 Exécution native sans Docker

Cette voie est destinée au développement avancé et demande Python 3.13, `uv`, Node.js 24, Corepack/pnpm, Redis, Tesseract, Poppler et les bibliothèques système attendues par Paperless-ngx. PostgreSQL est recommandé pour se rapprocher de la production.

```bash
uv sync --python 3.13 --group dev
cd src-ui
corepack enable
pnpm install
pnpm exec ng build --configuration production --localize
cd ..
export PAPERLESS_SECRET_KEY="$(uv run python -c 'import secrets; print(secrets.token_urlsafe(64))')"
export PAPERLESS_REDIS=redis://localhost:6379
uv run python src/manage.py migrate
uv run daphne -b 0.0.0.0 -p 8000 paperless.asgi:application
```

Dans un second terminal, avec les mêmes variables :

```bash
uv run celery --app paperless worker -l INFO
```

Les chemins et paquets système varient selon la distribution. En production, utiliser l’image Docker livrée plutôt que de reproduire manuellement son environnement.

## 9. Base de données et migrations

Les migrations GED-SARTEX font partie du dépôt et sont appliquées automatiquement au démarrage de l’image. Ne pas lancer `makemigrations` en production. Avant une mise à jour :

```bash
docker compose exec webserver python manage.py showmigrations documents paperless
```

Après déploiement :

```bash
docker compose exec webserver python manage.py migrate --check
```

Ne jamais modifier manuellement les tables d’armoires, signatures ou workflows. Toute évolution du schéma doit être réalisée par une migration Django testée sur une copie de la base.

Pour intégrer ultérieurement de nouvelles versions de Paperless-ngx, créer une branche, fusionner l’amont, résoudre les conflits, exécuter les migrations et la suite de tests, puis construire une nouvelle image. Ne jamais remplacer uniquement des fichiers Python dans un conteneur déjà en production.

## 10. Sauvegarde et restauration

### 10.1 Ce qu’il faut sauvegarder

- base PostgreSQL : documents, utilisateurs, permissions, armoires, demandes, états et historique des workflows ;
- volume `media` : originaux, archives, miniatures, signatures et copies signées ;
- volume `data` : index et données applicatives ;
- dossiers `consume` et `export` selon les besoins ;
- `.env` et `paperless.env` dans un coffre de secrets, séparément des sauvegardes ordinaires.

Une sauvegarde cohérente doit associer la base et les fichiers du même instant. Utiliser l’exporteur Paperless-ngx pour une sauvegarde logique portable et conserver en plus des sauvegardes de volumes/base.

Exemple d’export applicatif :

```bash
docker compose exec -T webserver document_exporter ../export
```

Tester régulièrement une restauration sur une instance isolée. Un fichier de sauvegarde jamais restauré ne constitue pas une preuve de reprise.

### 10.2 Restauration

1. arrêter l’écriture et relever le tag d’image utilisé ;
2. restaurer PostgreSQL et les volumes à partir du même point de sauvegarde ;
3. replacer les secrets d’origine, particulièrement `PAPERLESS_SECRET_KEY` ;
4. redémarrer avec la même image ;
5. exécuter les contrôles de cohérence et la recette fonctionnelle ;
6. seulement ensuite effectuer une mise à niveau.

Changer `PAPERLESS_SECRET_KEY` invalide des sessions et jetons signés. Le conserver comme un secret durable et sauvegardé.

## 11. Mise à jour et retour arrière

### Mise à jour

```bash
git fetch --tags
git checkout <NOUVEAU_TAG>
cd deployment
docker compose build --pull webserver
docker compose up -d
docker compose logs -f webserver
```

Faire la sauvegarde avant la construction. Examiner les migrations et notes de version. Tester sur une copie de données avant la production.

### Retour arrière

Un retour de code ne suffit pas si des migrations ont modifié la base. La procédure sûre consiste à restaurer ensemble la base et les volumes sauvegardés avant la mise à jour, puis à relancer l’ancien tag d’image.

## 12. Supervision et commandes d’exploitation

```bash
docker compose ps
docker compose logs --tail=200 webserver
docker compose logs --tail=200 db broker
docker compose restart webserver
docker compose exec webserver python manage.py check
```

Surveiller : espace disque, santé PostgreSQL/Valkey, croissance de `media`, échecs OCR, file Celery, erreurs de migration, réponses HTTP 4xx/5xx, workflows échoués et demandes de signature en échec.

## 13. Dépannage ciblé

### L’application refuse de démarrer avec `PAPERLESS_SECRET_KEY`

La valeur est absente ou restée à `change-me`. Générer un secret, le placer dans `paperless.env`, puis recréer le service :

```bash
docker compose up -d --force-recreate webserver
```

### Le frontend ne montre pas les nouveautés

L’image ou les fichiers statiques ne correspondent pas au code :

```bash
docker compose build --no-cache webserver
docker compose up -d --force-recreate webserver
```

Puis effectuer un rechargement complet du navigateur. En développement, reconstruire Angular avec `--localize`.

### « Upload complete, waiting… » ne disparaît pas

Vérifier le worker, Redis et Daphne/WebSocket :

```bash
docker compose logs webserver
docker compose logs broker
```

En développement, ne pas lancer uniquement Django `runserver` si l’on valide les notifications temps réel ; lancer Daphne et Celery.

### Erreur de permission pnpm dans le Dev Container

Utiliser les volumes anonymes Linux déjà déclarés dans `.devcontainer/docker-compose.devcontainer.sqlite-tika.yml`. Reconstruire le Dev Container si un ancien `node_modules` appartenant à root subsiste. Ne pas partager un `node_modules` Windows dans le conteneur.

### Une signature ou un workflow n’avance pas

Vérifier : permission de consultation du signataire, appartenance au groupe Signataires, présence d’un profil de signature, état de la demande, worker actif, activité du workflow et message d’erreur de l’étape. Les workflows séquentiels attendent explicitement la fin d’une étape humaine.

## 14. Sécurité avant mise en production

- secrets uniques, non commités et stockés dans un coffre ;
- TLS obligatoire hors réseau local ;
- pas d’exposition publique de PostgreSQL, Valkey, Tika ou Gotenberg ;
- principe du moindre privilège pour utilisateurs, groupes, armoires, documents et copies signées ;
- comptes administrateurs séparés des comptes quotidiens ;
- revue des utilisateurs du groupe Signataires ;
- validation des permissions des copies signées indépendamment du document ;
- sauvegardes chiffrées et tests de restauration ;
- mises à jour de sécurité planifiées ;
- journalisation et surveillance des rejets, suppressions et échecs de workflow ;
- revue juridique avant toute affirmation de signature électronique légale.

## 15. Publication du dépôt

Rendre le dépôt public facilite fortement le transfert, la construction Docker et le respect de la licence GPL-3.0 du projet amont. C’est recommandé uniquement après :

1. autorisation du propriétaire du projet et absence de code/données confidentiels ;
2. vérification de tout l’historique Git, pas seulement du dernier état ;
3. suppression ou rotation de tout secret, jeton, mot de passe, URL interne et donnée personnelle ;
4. maintien des avis de licence et d’attribution Paperless-ngx ;
5. ajout d’un tag de livraison et d’une description claire du caractère dérivé/non officiel.

Un dépôt privé peut parfaitement être livré à des collaborateurs autorisés. Dans ce cas, le serveur ou le pipeline doit disposer d’un accès Git/GHCR. Ne jamais rendre public uniquement pour contourner un problème d’authentification.

## 16. Critères de transfert au repreneur

Le repreneur doit recevoir : le tag/hash exact, les guides, le Compose, les secrets par canal séparé, une sauvegarde testée, un compte administrateur remis de façon sûre, la vidéo de démonstration et la liste des écarts connus. Il doit confirmer qu’il sait construire l’image, restaurer une sauvegarde, ajouter un utilisateur, gérer les permissions, traiter une signature et diagnostiquer un workflow.
