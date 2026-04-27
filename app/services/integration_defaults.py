INTEGRATION_DEFAULTS = {
    "github": {
        "client_id_env": "GITHUB_CLIENT_ID",
        "client_secret_env": "GITHUB_CLIENT_SECRET",
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "redirect_uri_env": "GITHUB_REDIRECT_URI",
        "scopes": "repo read:user read:org user:email",
        "type": "oauth"
    },
    "slack": {
        "client_id_env": "SLACK_CLIENT_ID",
        "client_secret_env": "SLACK_CLIENT_SECRET",
        "authorize_url": "https://slack.com/oauth/v2/authorize",
        "token_url": "https://slack.com/api/oauth.v2.access",
        "redirect_uri_env": "SLACK_REDIRECT_URI",
        "scopes": "channels:history channels:read groups:read users:read users:read.email team:read",
        "type": "oauth"
    },
    "jira": {
        "client_id_env": "JIRA_CLIENT_ID",
        "client_secret_env": "JIRA_CLIENT_SECRET",
        "authorize_url": "https://auth.atlassian.com/authorize",
        "token_url": "https://auth.atlassian.com/oauth/token",
        "redirect_uri_env": "JIRA_REDIRECT_URI",
        "scopes": "read:jira-work read:jira-user offline_access",
        "type": "oauth"
    },
    "figma": {
        "client_id_env": "FIGMA_CLIENT_ID",
        "client_secret_env": "FIGMA_CLIENT_SECRET",
        "authorize_url": "https://www.figma.com/oauth",
        "token_url": "https://www.figma.com/api/oauth/token",
        "redirect_uri_env": "FIGMA_REDIRECT_URI",
        "scopes": "file_read",
        "type": "oauth"
    },
    "gitlab": {
        "client_id_env": "GITLAB_CLIENT_ID",
        "client_secret_env": "GITLAB_CLIENT_SECRET",
        "authorize_url": "https://gitlab.com/oauth/authorize",
        "token_url": "https://gitlab.com/oauth/token",
        "redirect_uri_env": "GITLAB_REDIRECT_URI",
        "scopes": "read_api read_user read_repository",
        "type": "oauth"
    },
    "notion": {
        "client_id_env": "NOTION_CLIENT_ID",
        "client_secret_env": "NOTION_CLIENT_SECRET",
        "authorize_url": "https://api.notion.com/v1/oauth/authorize",
        "token_url": "https://api.notion.com/v1/oauth/token",
        "redirect_uri_env": "NOTION_REDIRECT_URI",
        "scopes": "database.read content.read",
        "type": "oauth"
    },
    "asana": {
        "client_id_env": "ASANA_CLIENT_ID",
        "client_secret_env": "ASANA_CLIENT_SECRET",
        "authorize_url": "https://app.asana.com/-/oauth_authorize",
        "token_url": "https://app.asana.com/-/oauth_token",
        "redirect_uri_env": "ASANA_REDIRECT_URI",
        "scopes": "default",
        "type": "oauth"
    },
    "teams": {
        "client_id_env": "TEAMS_CLIENT_ID",
        "client_secret_env": "TEAMS_CLIENT_SECRET",
        "authorize_url": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "redirect_uri_env": "TEAMS_REDIRECT_URI",
        "scopes": "User.Read Group.Read.All ChannelMessage.Read.All",
        "type": "oauth"
    },
    "discord": {
        "client_id_env": "DISCORD_CLIENT_ID",
        "client_secret_env": "DISCORD_CLIENT_SECRET",
        "authorize_url": "https://discord.com/api/oauth2/authorize",
        "token_url": "https://discord.com/api/oauth2/token",
        "redirect_uri_env": "DISCORD_REDIRECT_URI",
        "scopes": "identify email guilds",
        "type": "oauth"
    },
    "clickup": {
        "scopes": "",  
        "type": "apikey",
    },
    "linear": {
        "scopes": "",  
        "type": "apikey",
    },
    "trello": {
        "scopes": "",
        "type": "apikey"
    }
}
