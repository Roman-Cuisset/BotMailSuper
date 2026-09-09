# 📧 Configuration Gmail API - Guide Complet

Ce guide vous explique comment configurer Gmail API pour votre bot Telegram. L'opération est **100% gratuite** et prend environ 10-15 minutes.

## 📋 Prérequis

- Un compte Gmail (celui que vous utiliserez pour envoyer des emails)
- Un navigateur web
- Accès à Google Cloud Console

---

## 🚀 Étape 1 : Créer un projet Google Cloud

1. **Allez sur** : [Google Cloud Console](https://console.cloud.google.com/)

2. **Créez un nouveau projet** :
   - Cliquez sur le menu déroulant du projet (en haut à gauche)
   - Cliquez sur **"Nouveau projet"**
   - Nom du projet : `Telegram Mail Bot` (ou votre choix)
   - Cliquez sur **"Créer"**

3. **Attendez** que le projet soit créé (environ 10 secondes)

---

## 🔧 Étape 2 : Activer Gmail API

1. **Dans votre projet** créé, allez dans le menu ☰ (hamburger)
   - Sélectionnez **"APIs et services"** → **"Bibliothèque"**

2. **Recherchez** "Gmail API" dans la barre de recherche

3. **Cliquez** sur "Gmail API"

4. **Cliquez** sur le bouton bleu **"Activer"**

5. **Attendez** l'activation (quelques secondes)

---

## 🔑 Étape 3 : Créer des credentials OAuth 2.0

### 3.1 Configurer l'écran de consentement

1. Dans **"APIs et services"**, cliquez sur **"Écran de consentement OAuth"**

2. **Sélectionnez** : **"Externe"** (sauf si vous avez Google Workspace)

3. **Cliquez** sur **"Créer"**

4. **Remplissez** les informations obligatoires :
   - **Nom de l'application** : `Telegram Mail Bot`
   - **E-mail d'assistance utilisateur** : Votre email Gmail
   - **E-mail du développeur** : Votre email Gmail

5. **Cliquez** sur **"Enregistrer et continuer"**

6. **Portées (Scopes)** :
   - Cliquez sur **"Ajouter ou supprimer des portées"**
   - Recherchez et sélectionnez : `https://www.googleapis.com/auth/gmail.send`
   - Cliquez sur **"Mettre à jour"**
   - Cliquez sur **"Enregistrer et continuer"**

7. **Utilisateurs test** :
   - Cliquez sur **"Ajouter des utilisateurs"**
   - Ajoutez votre adresse Gmail (celle qui enverra les emails)
   - Cliquez sur **"Enregistrer et continuer"**

8. **Vérifiez** le résumé et cliquez sur **"Retour au tableau de bord"**

### 3.2 Créer les credentials

1. Dans **"APIs et services"**, cliquez sur **"Identifiants"**

2. Cliquez sur **"+ Créer des identifiants"** en haut

3. Sélectionnez **"ID client OAuth"**

4. **Type d'application** : Sélectionnez **"Application de bureau"**

5. **Nom** : `Telegram Bot Desktop`

6. Cliquez sur **"Créer"**

7. **Une popup apparaît** avec vos credentials :
   - ✅ **Cliquez sur "Télécharger JSON"**
   - 📥 Enregistrez le fichier

---

## 📁 Étape 4 : Installer le fichier credentials.json

1. **Renommez** le fichier téléchargé en `credentials.json`

2. **Placez** ce fichier dans le dossier de votre bot :
   ```
   c:\Users\stcui\Documents\Bot\telegram_mail_bot\credentials.json
   ```

3. **Vérifiez** que le fichier est bien au bon endroit (même niveau que `main_pro.py`)

---

## 🔐 Étape 5 : Première authentification

Cette étape sera effectuée **automatiquement** lors du premier envoi d'email avec Gmail API.

**Ce qui va se passer** :

1. Un navigateur s'ouvrira automatiquement
2. Google vous demandera de vous connecter
3. Un avertissement apparaîtra : **"Cette application n'est pas validée par Google"**
   - C'est **normal** car c'est votre propre application
   - Cliquez sur **"Paramètres avancés"**
   - Cliquez sur **"Accéder à Telegram Mail Bot (dangereux)"**
4. Autorisez l'application à envoyer des emails
5. Le navigateur affichera : **"L'authentification a réussi"**
6. Un fichier `token.json` sera créé automatiquement

> [!IMPORTANT]
> **Vous ne devrez faire cette authentification qu'une seule fois !**
> Le fichier `token.json` stockera vos credentials pour les prochaines utilisations.

---

## ✅ Vérification

Après l'installation :

1. ✅ `credentials.json` existe dans le dossier du bot
2. ✅ Gmail API est activée dans Google Cloud Console
3. ✅ Votre email est listé comme utilisateur test
4. ✅ Après la première authentification, `token.json` existe

---

## 🔧 Dépannage

### Problème : "credentials.json not found"
**Solution** : Vérifiez que le fichier est bien nommé `credentials.json` (pas `client_secret_xxx.json`)

### Problème : "Access blocked: This app's request is invalid"
**Solution** : Vérifiez que vous avez bien ajouté le scope `https://www.googleapis.com/auth/gmail.send`

### Problème : "The user did not consent"
**Solution** : Assurez-vous d'avoir cliqué sur "Autoriser" dans la fenêtre d'authentification

### Problème : Le navigateur ne s'ouvre pas automatiquement
**Solution** : 
1. Cherchez dans les logs du bot une URL commençant par `https://accounts.google.com/...`
2. Copiez cette URL et ouvrez-la manuellement dans votre navigateur

---

## 📊 Quotas gratuits

| Opération | Quota gratuit |
|-----------|---------------|
| Envoi d'emails | **1 milliard/jour** |
| Requêtes API | **1 milliard/jour** |
| Coût | **0€** |

> [!TIP]
> Gmail API a des quotas bien plus élevés que le SMTP traditionnel et offre une meilleure délivrabilité !

---

## 🔒 Sécurité

> [!CAUTION]
> **Ne partagez JAMAIS vos fichiers** :
> - ❌ `credentials.json`
> - ❌ `token.json`
> - ❌ `secrets.env`
>
> Ces fichiers contiennent des informations sensibles !

---

## 📞 Support

Si vous rencontrez des problèmes :

1. Vérifiez les logs du bot dans `bot_log.txt`
2. Consultez la section **Dépannage** ci-dessus
3. Vérifiez que tous les fichiers sont au bon endroit
