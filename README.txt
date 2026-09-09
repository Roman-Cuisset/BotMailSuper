=== TELEGRAM MAIL BOT PRO ===

📦 Ce bot vous permet d'envoyer par email :
- Des textes, photos et documents reçus sur Telegram
- Avec confirmation d'envoi
- Enregistrement local automatique par utilisateur/date
- Historique chiffré
- Anti-spam + interface interactive

---

🔧 INSTALLATION :

1. Installe Python 3.10 ou + sur ton PC
2. Ouvre un terminal dans le dossier du bot

3. Installe les dépendances :
> pip install -r requirements.txt

4. Crée un fichier `.env` (ou utilise `secrets.env`) et remplis avec :
> TELEGRAM_TOKEN=TON_TOKEN
> EMAIL_SENDER=TON_EMAIL
> EMAIL_PASSWORD=TON_MDP_APP
> SECRET_KEY=CLÉ_SECRÈTE
> WEB_SECRET_KEY=AUTRE_CLÉ_SECRÈTE_LONGUE
> ADMIN_PASSWORD=MOT_DE_PASSE_ADMIN_FORT
> ADMIN_IDS=IDENTIFIANT_TELEGRAM_ADMIN_1,IDENTIFIANT_ADMIN_2

Ne publiez jamais `secrets.env`, `credentials.json`, `token.pickle`, les fichiers
`.session`, la base de données ou les journaux. Utilisez `secrets.env.example`
comme modèle sans y placer de vraie valeur.

---

🚀 LANCER LE BOT :

> python main_pro.py

Il démarrera et t'affichera "🤖 Bot lancé"

---

📁 SAUVEGARDES :

Tous les fichiers reçus sont enregistrés dans :
> /TelegramMailBotFiles/@username/AAAA-MM-JJ/

---

📄 LOGS :
> Fichier : bot_log.txt

🕓 Historique chiffré :
> Fichier : history.json

