# BotMailSuper

BotMailSuper transforme rapidement un texte, une photo, un document ou un album Telegram en e-mail. Le projet comprend le bot, un panneau d’administration et une Telegram Mini App.

## Fonctions principales

- Envoi SMTP avec confirmation du résultat réel
- Sujet modifiable, prévisualisation et bouton de nouvelle tentative
- Contacts paginés et recherchables, groupes, modèles et brouillons
- Envois programmés, quotas, VIP, blacklist et statistiques
- Mini App : composer, contacts, brouillons, historique et compte SMTP
- Français, anglais et russe

L’ancienne intégration Gmail API a été supprimée. Le service utilise uniquement SMTP.

## Installation

1. Installer Python 3.10 ou plus récent et PM2.
2. Créer l’environnement : `python3 -m venv .venv`.
3. Installer les dépendances : `.venv/bin/pip install -r requirements.txt`.
4. Copier `secrets.env.example` vers `secrets.env`, puis renseigner les valeurs.
5. Installer `ngrok` dans `.tools/ngrok`, créer un compte gratuit puis renseigner `NGROK_AUTHTOKEN`.
6. Lancer les services : `./start.sh`.

PM2 démarre quatre processus :

- `bot-telegram` : bot Telegram et workers ;
- `bot-web` : administration sur le port 5000 ;
- `bot-miniapp` : Mini App locale sur le port 5010.
- `bot-public-tunnel` : domaine HTTPS ngrok fixe et synchronisation du bouton Telegram.

La Mini App exige une URL HTTPS accessible depuis le téléphone. Indiquer son URL complète, terminée par `/miniapp`, dans `WEBAPP_URL`. Le bouton Telegram est configuré automatiquement au prochain redémarrage du bot.

En production locale, le processus `bot-public-tunnel` maintient le domaine de développement ngrok gratuit, écrit l'URL active dans `.runtime/public_url` et met à jour le bouton Telegram. Aucun domaine acheté ni port ouvert sur la box n'est nécessaire, et le domaine ngrok reste identique après un redémarrage.

## Administration

Ouvrir `/login` sur le port 5000. Le premier démarrage transforme automatiquement `ADMIN_PASSWORD` en hash persistant dans SQLite. Un changement effectué dans **Settings** est durable. Les connexions sont protégées par CSRF, cookies renforcés, expiration de session et limitation des tentatives.

## Tests

```bash
.venv/bin/python -m unittest -v test_core.py
.venv/bin/python verify_refactor.py
.venv/bin/python test_improvements.py
.venv/bin/python test_email_rendering.py
.venv/bin/python test_i18n.py
```

## Données et sécurité

Ne jamais publier `secrets.env`, la base SQLite, les journaux, les sessions ou les jetons. Les pièces jointes restent en mémoire le temps de l’envoi et ne sont pas conservées sur disque. Les logs tournent automatiquement et masquent les adresses destinataires. L’historique de plus de 30 jours est supprimé quotidiennement lorsque `AUTO_CLEANUP_ENABLED` est actif.
