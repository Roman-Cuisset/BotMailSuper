# 🧪 Gmail API - Guide de Test

Ce guide vous aide à tester l'intégration Gmail API après sa configuration.

## ⚠️ Prérequis avant les tests

Avant de tester, vous **DEVEZ** avoir complété les étapes du guide [GMAIL_API_SETUP.md](GMAIL_API_SETUP.md) :

- ✅ Projet Google Cloud créé
- ✅ Gmail API activée
- ✅ Credentials OAuth 2.0 créés
- ✅ Fichier `credentials.json` téléchargé et placé dans le dossier du bot
- ✅ Bot redémarré

## 🔍 Vérification de la configuration

### Test 1 : Vérifier que les fichiers sont en place

```bash
# Vérifiez que credentials.json existe
ls credentials.json

# Vérifiez que USE_GMAIL_API est activé
cat secrets.env | grep USE_GMAIL_API
```

**Résultat attendu** :
- `credentials.json` existe
- `USE_GMAIL_API=True` dans `secrets.env`

---

## 🧪 Tests fonctionnels

### Test 2 : Premier email (Authentification OAuth)

1. **Envoyez un email via le bot Telegram** :
   - Utilisez la commande normale du bot pour envoyer un email
   - Exemple : Envoyez un message à n'importe quelle adresse email

2. **Lors du premier envoi** :
   - Un navigateur devrait s'ouvrir automatiquement
   - Vous verrez la page d'authentification Google
   - **Suivez les instructions** dans [GMAIL_API_SETUP.md - Étape 5](GMAIL_API_SETUP.md#étape-5--première-authentification)

3. **Après authentification** :
   - Le fichier `token.json` sera créé automatiquement
   - L'email devrait être envoyé via Gmail API

4. **Vérifiez les logs** :
   ```bash
   tail -n 50 bot_log.txt | grep "Gmail API"
   ```

**Résultat attendu** :
```
✅ Gmail API service initialized
📧 Attempting to send email via Gmail API to test@example.com...
✅ Email sent successfully via Gmail API! Message ID: xxxxx
```

---

### Test 3 : Email avec pièce jointe

1. **Envoyez un email avec une image ou un PDF** via Telegram
2. **Vérifiez la réception** dans la boîte mail du destinataire
3. **Vérifiez** que la pièce jointe est bien présente et téléchargeable

**Résultat attendu** :
- Email reçu avec pièce jointe intacte
- Log : `✅ Email sent via Gmail API to ...`

---

### Test 4 : Email HTML et template

1. **Envoyez un email simple** (sans HTML)
2. **Vérifiez** que le destinataire reçoit l'email avec le **template personnalisé** (receptiondesing.html)

**Résultat attendu** :
- Email avec le design personnalisé
- Nom de l'expéditeur visible
- Liste des pièces jointes bien formatée

---

### Test 5 : Signature VIP

**Prérequis** : Vous devez être un utilisateur VIP avec une signature définie

1. **Configurez une signature VIP** via `/setsignature`
2. **Envoyez un email** en tant qu'utilisateur VIP
3. **Vérifiez** que la signature apparaît à la fin de l'email

**Résultat attendu** :
- Signature présente à la fin du message
- Séparateur `---` avant la signature

---

### Test 6 : Fallback SMTP

Ce test vérifie que le système bascule automatiquement vers SMTP si Gmail API échoue.

1. **Désactivez Gmail API temporairement** :
   - Modifiez `secrets.env` : `USE_GMAIL_API=False`
   - Redémarrez le bot

2. **Envoyez un email**

3. **Vérifiez les logs** :
   ```bash
   tail -n 20 bot_log.txt | grep "SMTP"
   ```

**Résultat attendu** :
```
📧 Sending email via SMTP to test@example.com...
✅ Email sent via SMTP to test@example.com
```

4. **Réactivez Gmail API** :
   - Modifiez `secrets.env` : `USE_GMAIL_API=True`
   - Redémarrez le bot

---

### Test 7 : Broadcast (envoi multiple)

1. **Utilisez la commande `/broadcast`** (si vous êtes admin)
2. **Envoyez un message** à plusieurs utilisateurs
3. **Vérifiez** que tous les emails sont envoyés

**Résultat attendu** :
- Tous les emails envoyés via Gmail API
- Logs confirmant chaque envoi

---

### Test 8 : Rapport hebdomadaire

1. **Exécutez le générateur de rapport** :
   ```bash
   python utils/report_generator.py
   ```

2. **Vérifiez** la réception du rapport dans votre boîte mail

**Résultat attendu** :
- Rapport HTML bien formaté reçu
- Log : `✅ Weekly report sent via Gmail API to ...`

---

## 🔍 Vérification des logs

### Vérifier que Gmail API est actif

```bash
grep "Gmail API" bot_log.txt | tail -n 20
```

**Messages positifs** :
- ✅ `Gmail API module loaded`
- ✅ `Gmail API service initialized`
- ✅ `Email sent successfully via Gmail API`

**Messages d'avertissement** :
- ⚠️ `Gmail API failed, falling back to SMTP` (normal si credentials manquants)
- ⚠️ `Gmail API not available` (module non installé)

---

## 🐛 Dépannage

### Problème : "credentials.json not found"

**Solution** :
1. Vérifiez que `credentials.json` est dans le bon dossier
2. Chemin complet : `c:\Users\stcui\Documents\Bot\telegram_mail_bot\credentials.json`

### Problème : "The user did not consent"

**Solution** :
1. Supprimez `token.json` s'il existe
2. Relancez un envoi d'email
3. Complétez l'authentification OAuth dans le navigateur

### Problème : "Gmail API HTTP error 401"

**Solution** :
1. Le token a expiré
2. Supprimez `token.json`
3. Réauthentifiez en envoyant un nouvel email

### Problème : Le navigateur ne s'ouvre pas

**Solution** :
1. Cherchez dans `bot_log.txt` une URL commençant par `https://accounts.google.com/...`
2. Copiez cette URL et ouvrez-la manuellement dans votre navigateur

### Problème : Emails toujours envoyés via SMTP

**Solutions** :
1. Vérifiez `USE_GMAIL_API=True` dans `secrets.env`
2. Redémarrez le bot
3. Vérifiez que `credentials.json` existe
4. Vérifiez les logs pour voir les erreurs

---

## 📊 Comparaison SMTP vs Gmail API

| Critère | SMTP | Gmail API |
|---------|------|-----------|
| **Authentification** | Mot de passe d'application | OAuth 2.0 |
| **Fiabilité** | Bonne | Excellente |
| **Limites d'envoi** | ~500/jour | ~1 milliard/jour |
| **Délivrabilité** | Standard | Supérieure |
| **Tracking** | Non | Message ID disponible |
| **Révocation** | Possible | Facile (via Google Cloud) |

---

## ✅ Checklist finale

Après tous les tests :

- [ ] Premier email envoyé et authentification OAuth réussie
- [ ] `token.json` créé automatiquement
- [ ] Emails avec pièces jointes fonctionnent
- [ ] Template HTML s'affiche correctement
- [ ] Signatures VIP ajoutées correctement
- [ ] Fallback SMTP fonctionne si Gmail API désactivé
- [ ] Broadcast fonctionne
- [ ] Rapports hebdomadaires envoyés correctement
- [ ] Logs indiquent clairement "Gmail API" ou "SMTP"

---

## 🎉 Félicitations !

Si tous les tests passent, votre intégration Gmail API est **complète et fonctionnelle** ! 🚀

Vous pouvez maintenant profiter de :
- ✅ Meilleure délivrabilité
- ✅ Quotas plus élevés
- ✅ Authentification OAuth sécurisée
- ✅ Fallback automatique vers SMTP
