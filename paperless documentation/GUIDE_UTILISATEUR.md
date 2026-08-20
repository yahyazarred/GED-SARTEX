# Guide utilisateur détaillé — GED-SARTEX

## 1. Concepts essentiels

GED-SARTEX centralise les documents, extrait leur texte par OCR et permet de les retrouver par recherche, attributs et permissions. Les éléments principaux sont :

- **document** : original importé, archive OCR, métadonnées et versions ordinaires ;
- **tag** : étiquette multiple et transversale ;
- **correspondant** : personne ou organisation liée au document ;
- **type de document** : nature fonctionnelle, par exemple facture ou contrat ;
- **armoire** : classement principal ajouté par GED-SARTEX, avec permissions héritables ;
- **copie signée** : PDF final issu d’une demande de signature, conservé séparément des versions ordinaires ;
- **workflow** : déclencheur suivi d’actions exécutées dans un ordre déterminé ;
- **approbation** : décision humaine qui bloque la suite jusqu’à acceptation ou rejet.

Les menus visibles dépendent des permissions. L’absence d’un écran n’est pas nécessairement une erreur : demander à l’administrateur les droits nécessaires.

## 2. Connexion, langue et profil

Se connecter avec le compte fourni. Dans les paramètres du profil, choisir **Français** puis enregistrer et recharger la page. Les libellés ajoutés pour les armoires, signatures et workflows disposent d’une traduction française ; certains textes hérités de bibliothèques ou messages techniques peuvent rester en anglais.

Ne jamais partager son mot de passe ou son jeton API. Le jeton API est réservé aux intégrations et doit être révoqué lorsqu’il n’est plus utilisé.

## 3. Importer et traiter un document

Un document peut être ajouté depuis le bouton d’envoi, glissé dans l’interface ou placé dans le dossier `consume` par un opérateur autorisé. Après l’envoi :

1. le fichier est accepté ;
2. le worker effectue l’OCR et la conversion ;
3. les règles de correspondance et workflows peuvent s’exécuter ;
4. le document devient disponible dans la liste.

Si « en attente » reste affiché alors que le document existe, recharger une fois puis signaler l’incident si le problème persiste : les notifications temps réel ou le worker peuvent être indisponibles.

Dans la fiche du document, vérifier le titre, la date, le correspondant, le type, les tags, l’armoire, les champs personnalisés et les permissions. Les traitements automatiques doivent toujours être contrôlés pour les documents sensibles.

## 4. Rechercher et organiser

Utiliser la barre de recherche pour le texte OCR, les titres et les métadonnées. Combiner la recherche avec les filtres de tags, correspondants, types, armoires, dates, propriétaires et champs personnalisés. Les vues enregistrées permettent de conserver une recherche fréquente.

Un filtre ne donne jamais un droit supplémentaire : un utilisateur ne voit que les objets qu’il est autorisé à consulter.

## 5. Armoires

### 5.1 Créer une armoire

Un utilisateur doit posséder l’autorisation d’ajouter des armoires. Depuis **Attributs** ou **Armoires**, créer l’armoire, saisir son nom et, si souhaité, configurer son algorithme de correspondance comme pour les tags et types.

Définir ensuite les permissions de consultation et de modification pour les utilisateurs ou groupes concernés. La permission globale de voir les armoires contrôle l’accès au type d’objet ; les permissions objet contrôlent l’accès à une armoire précise.

### 5.2 Affecter un document

Dans la fiche du document, choisir une armoire. Depuis l’écran **Armoires**, rechercher ou filtrer la liste, puis ouvrir une armoire pour accéder à la liste des documents filtrée sur cette armoire. L’interface indique le contexte de l’armoire active.

Un document appartient à une armoire à la fois dans cette implémentation. Les tags restent adaptés aux classements multiples.

### 5.3 Correspondance automatique

Une armoire peut reprendre les mécanismes de correspondance disponibles pour les autres attributs : texte, règles et algorithmes proposés par l’interface. Tester la règle sur un échantillon avant de l’activer à grande échelle. Une action de workflow peut aussi lancer la correspondance automatique ou affecter explicitement une armoire.

### 5.4 Héritage des permissions

Le commutateur **Hériter des permissions de l’armoire** détermine la politique du document :

- activé : les droits de consultation et modification de l’armoire servent pour le document ;
- désactivé : les permissions propres au document peuvent être gérées indépendamment.

Cet héritage concerne la consultation et la modification. La suppression reste un droit distinct et sensible. Pour cacher un document à un membre normalement autorisé sur l’armoire, désactiver l’héritage puis définir explicitement les personnes et groupes autorisés sur le document.

Après tout changement, tester avec un compte non administrateur. Un superutilisateur n’est pas un bon compte de validation, car il contourne de nombreux contrôles.

## 6. Utilisateurs, groupes et permissions

### 6.1 Permissions globales et permissions objet

Les permissions globales autorisent une catégorie d’opération, par exemple ajouter ou voir des armoires, demander une signature, voir des workflows ou superviser leur activité. Les permissions objet limitent l’accès à une armoire, un document ou une copie signée déterminée.

Accorder uniquement les droits nécessaires :

- consultation pour lire/télécharger ;
- modification pour changer les métadonnées ou gérer ce que l’écran autorise ;
- suppression pour détruire ;
- ajout pour créer un objet de ce type.

### 6.2 Groupes intégrés

Les groupes intégrés sont des groupes système distingués des groupes personnalisés. Ils ne peuvent pas être supprimés ni transformés en groupes ordinaires. Le groupe **Signataires** active l’accès au parapheur pour ses membres. Les permissions du groupe peuvent être administrées conformément à la politique du site.

L’appartenance au groupe Signataires ne donne pas automatiquement accès à tous les documents : le signataire doit aussi pouvoir consulter le document concerné pour apparaître comme destinataire d’une demande.

### 6.3 Bon modèle de rôles

- administrateurs techniques : configuration, sauvegarde et dépannage ;
- administrateurs fonctionnels : utilisateurs, groupes, attributs et workflows ;
- demandeurs de signature : permission dédiée, uniquement sur les documents qu’ils consultent ;
- signataires : groupe Signataires et droits ciblés sur les documents ;
- superviseurs : permission de voir l’activité des workflows ;
- lecteurs : consultation minimale par groupe/armoire.

Éviter d’attribuer des permissions individuellement à grande échelle ; préférer les groupes, puis utiliser les exceptions objet avec parcimonie.

## 7. Signature visuelle

### 7.1 Limite juridique

La fonctionnalité appose une image de signature et produit un PDF signé visuellement. Elle enregistre le demandeur, le signataire, la version source, l’emplacement et des empreintes de fichiers. Elle n’implémente pas une signature cryptographique qualifiée, un certificat de confiance, un horodatage qualifié ni une vérification d’identité forte.

### 7.2 Préparer le signataire

L’administrateur :

1. ajoute l’utilisateur au groupe intégré **Signataires** ;
2. lui accorde la consultation des documents à signer, directement ou par groupe/armoire ;
3. vérifie que l’onglet **Demandes de signature** ou **Parapheur** apparaît après reconnexion.

Le signataire ouvre le parapheur, choisit **Modifier ma signature**, puis dépose un PNG, PDF ou autre format accepté. L’application prépare une version avec fond supprimé lorsque possible. Seul le signataire peut voir et modifier son propre fichier de signature.

Avant d’enregistrer, contrôler l’aperçu immédiat. Une signature avec fond uniforme et fort contraste produit généralement le meilleur résultat.

### 7.3 Demander une signature

Dans la fiche du document, ouvrir l’onglet **Signatures** puis :

1. choisir un seul signataire ;
2. ajouter un message facultatif ;
3. envoyer la demande.

La liste exclut le demandeur lui-même et les signataires qui ne peuvent pas consulter le document. Une seule demande en attente ou en traitement est permise pour le même document, la même version et le même signataire. Après création d’une copie signée, le même signataire ne peut pas signer une seconde fois la même version tant que cette copie existe. Une autre version peut faire l’objet d’une nouvelle demande.

Le demandeur peut suivre les états : en attente, traitement, signée, rejetée, annulée ou échouée. Les couleurs facilitent la lecture. Les demandes annulées et terminées restent dans l’historique.

### 7.4 Traiter une demande dans le parapheur

Le parapheur ne présente à chaque signataire que les demandes qui lui sont assignées. Le badge rouge indique le nombre de demandes en attente et se met à jour avec les événements de l’application.

Le signataire peut :

- ouvrir la demande et lire le message ;
- rejeter en saisissant un motif ;
- accepter, ouvrir l’aperçu du PDF, faire glisser sa signature, la redimensionner et la positionner sans masquer le contenu ;
- confirmer la signature.

La vue conserve également l’historique des demandes signées, rejetées et annulées. En cas d’échec, ne pas créer une seconde demande sans examiner le message et l’activité du workflow éventuel.

### 7.5 Copies signées

Dans **Signatures → Copies signées**, les PDF signés sont regroupés avec le signataire, la version source, le demandeur et la date. Ces copies ne sont pas des documents ordinaires et n’encombrent pas la corbeille comme plusieurs documents indépendants.

Les permissions d’une copie signée sont indépendantes de celles du document. Le bouton d’ouverture n’apparaît que si l’utilisateur peut consulter cette copie. Les utilisateurs autorisés à la gérer peuvent modifier ses permissions ou la supprimer selon leurs droits. L’utilisateur courant n’est pas proposé comme cible à retirer de ses propres permissions via l’interface.

Lorsqu’une copie signée est supprimée, la demande terminée reste visible et porte l’indication **Copie signée supprimée**. La suppression lève aussi la contrainte empêchant une nouvelle signature de cette version par le même signataire.

La mise à la corbeille puis la suppression d’un document doit entraîner le nettoyage de ses copies signées selon le cycle prévu, sans créer plusieurs entrées de document ordinaires.

### 7.6 Qui peut voir quoi

- le fichier de signature personnel : uniquement son signataire ;
- une demande : son signataire, son demandeur et les acteurs administratifs autorisés selon l’API/écran ;
- le parapheur : uniquement les demandes du signataire connecté ;
- une copie signée : uniquement les utilisateurs/groupes ayant la permission objet ou les administrateurs habilités ;
- l’historique du document : selon l’accès au document, avec les événements de demande, annulation, signature ou rejet.

## 8. Workflows séquentiels

### 8.1 Principe

Un workflow se construit comme une suite de briques : le premier bloc est le déclencheur, puis les actions numérotées s’exécutent dans l’ordre. Une action ne démarre pas avant la réussite de la précédente. Une approbation ou une signature place l’exécution en attente jusqu’à la décision humaine.

Le terme « workflow » est utilisé dans l’interface. Certains noms techniques historiques peuvent encore contenir `Circuit` dans le code ou l’API ; ils ne désignent pas un second produit.

### 8.2 Créer le déclencheur

Depuis **Workflows**, créer ou modifier un workflow. Définir son nom et son ordre, puis le déclencheur initial : document ajouté, document mis à jour ou autre événement proposé. Ajouter des filtres pour limiter le lancement : source, mots présents, tags, types, correspondants, armoires ou critères disponibles.

Un déclencheur trop large peut démarrer des traitements sur tous les documents. Commencer avec des conditions précises et tester sur un document de recette.

### 8.3 Ajouter et ordonner les actions

Utiliser les signes **+** avant, entre ou après les étapes. Les actions portent un numéro d’ordre et peuvent être réorganisées. Actions disponibles selon la configuration :

- affectation de titre, tags, type, correspondant, chemin, armoire, propriétaire ou permissions ;
- retrait d’attributs ;
- envoi d’e-mail ;
- webhook ;
- suppression de mot de passe ;
- déplacement vers la corbeille ;
- approbation ;
- demande de signature ;
- correspondance automatique.

Enregistrer seulement après avoir renseigné le nom, l’ordre et les champs obligatoires. Si une validation échoue, corriger le champ signalé puis enregistrer à nouveau.

### 8.4 Étape d’approbation

Choisir exactement un utilisateur ou un groupe. Pour un groupe, sélectionner la règle :

- **un membre** : la première décision positive attendue permet d’avancer et les autres tâches en attente sont annulées ;
- **tous les membres** : chaque membre actif doit approuver.

Choisir l’accès temporaire accordé pendant l’attente : consultation, modification ou aucune modification de permissions. Ces droits sont retirés à la fin lorsque l’application les avait accordés pour cette tâche, sous réserve des autres droits que l’utilisateur possède déjà.

L’approbateur traite sa tâche dans **Approbation**, accepte ou rejette et peut fournir un commentaire. Un rejet peut arrêter le workflow ou emprunter une branche dédiée.

### 8.5 Étape de demande de signature

Choisir un signataire déterminé lors de la conception. À l’exécution, le workflow crée la demande et attend son résultat. Le signataire doit être actif, appartenir au groupe Signataires et être autorisé sur le document. Une signature réussie permet la suite ; un rejet, une annulation ou un échec applique la route de rejet configurée.

### 8.6 Correspondance et affectation d’armoire

L’action **Correspondance automatique** peut lancer les moteurs existants pour tags, armoire et autres attributs pris en charge. Une action d’affectation explicite est préférable lorsqu’un résultat déterministe est nécessaire. Elle peut aussi définir l’héritage des permissions de l’armoire.

### 8.7 Branches de rejet

Les étapes humaines peuvent avoir une route alternative. Les actions de branche sont repérées par des lettres, par exemple `2.a`, `2.b`, et apparaissent latéralement dans l’activité afin de ne pas être confondues avec la ligne principale.

Une branche de rejet constitue un chemin différent. Elle peut notifier, réaffecter, appliquer des tags, déplacer en corbeille ou réaliser d’autres actions disponibles. Elle ne rejoint pas automatiquement une étape principale ultérieure sauf si le modèle de workflow le prévoit explicitement. Concevoir la fin de chaque branche sans ambiguïté.

### 8.8 Activité et supervision

Les superutilisateurs et utilisateurs disposant de la permission de consultation de l’activité des workflows peuvent ouvrir **Activité des workflows**. Chaque exécution affiche son document, son état et ses étapes. La flèche développe des carrés numérotés : réussite en vert, attente, rejet ou échec avec leurs couleurs respectives ; les branches restent visuellement séparées.

Cliquer une étape pour consulter les heures, l’acteur, les détails, le motif de rejet et l’erreur technique éventuelle. Les commandes exposées doivent être utilisées avec prudence ; l’interface finale privilégie le suivi et l’action **Ignorer** lorsqu’elle est autorisée, sans proposer les anciennes opérations redondantes de réaffectation/réessai.

L’activité est conservée même si une branche déplace le document dans la corbeille. Les demandes de signature associées doivent également rester traçables.

## 9. Historique, versions et suppression

Les versions ordinaires d’un document et les copies signées sont deux ensembles distincts. Une copie signée référence précisément sa version source, mais n’est pas ajoutée à la liste des documents ordinaires.

L’historique du document enregistre notamment la création de demande, l’annulation, la signature et le rejet. L’activité du workflow fournit un niveau plus détaillé pour chaque étape.

Avant une suppression définitive : vérifier les copies signées, l’activité de workflow, les obligations de conservation et les sauvegardes. La corbeille est une étape de récupération ; elle ne remplace pas une politique d’archivage.

## 10. Procédures de contrôle par rôle

### Administrateur

- vérifier les groupes intégrés et personnalisés ;
- attribuer les permissions globales minimales ;
- tester les permissions objet avec des comptes de recette ;
- surveiller les workflows échoués et demandes bloquées ;
- contrôler les sauvegardes et l’espace disque ;
- revoir régulièrement les signataires et superviseurs.

### Gestionnaire documentaire

- contrôler l’OCR et les métadonnées ;
- corriger les correspondances automatiques ;
- appliquer l’armoire et la politique d’héritage ;
- surveiller les documents sans classement ;
- ne pas élargir les droits sans justification.

### Demandeur de signature

- choisir la bonne version et le bon signataire ;
- éviter les demandes inutiles ;
- suivre l’état et annuler seulement une demande encore en attente ;
- contrôler la copie signée et ses permissions après signature.

### Signataire

- protéger son compte et son fichier de signature ;
- vérifier le document et la version avant de signer ;
- positionner la signature sans masquer le texte ;
- motiver clairement un rejet ;
- signaler immédiatement toute demande qui ne lui est pas destinée.

## 11. Scénario de formation conseillé

1. créer deux groupes métiers, un demandeur et un signataire ;
2. créer une armoire avec droits de groupe ;
3. importer un document, vérifier l’OCR et l’affecter ;
4. démontrer l’héritage puis l’exception de permission document ;
5. demander une signature, la rejeter avec motif et consulter l’historique ;
6. refaire une demande sur une version autorisée, signer et gérer la copie ;
7. construire un workflow avec approbation, signature et affectation d’armoire ;
8. tester la branche de rejet ;
9. consulter l’activité avec un superviseur ;
10. exporter puis restaurer un jeu de test sur une instance isolée.

## 12. Règles de gouvernance recommandées

- convention de nommage des armoires, tags et workflows ;
- propriétaire fonctionnel pour chaque workflow ;
- revue trimestrielle des permissions et groupes ;
- interdiction de comptes partagés ;
- durée de conservation des documents et copies signées ;
- processus de révocation des signataires ;
- validation à quatre yeux des workflows qui suppriment ou déplacent des documents ;
- recette après chaque mise à jour ;
- documentation des écarts entre signature visuelle et signature réglementaire.
