# Guia de Build — GeoAdmin Pro Mobile

Este guia descreve os pré-requisitos, configurações e comandos necessários para gerar as versões de testes (APK) e produção (AAB para Google Play Store) do aplicativo móvel do **GeoAdmin Pro**, utilizando o **EAS Build** (Expo Application Services) sob a stack Expo 54.

---

## 📋 Pré-requisitos

1. **EAS CLI instalado globalmente (ou via npx):**
   ```bash
   npm install -g eas-cli
   ```
2. **Conta Expo:**
   Você precisará de uma conta no [Expo.dev](https://expo.dev) e estar logado no terminal:
   ```bash
   eas login
   ```
3. **Configuração do Projeto:**
   O arquivo `app.json` na raiz da pasta `mobile/` já está previamente configurado com o `slug`, `android.package`, `extra.eas.projectId` e `owner` oficiais.

---

## 🛠️ Perfis de Build (Configuração no `eas.json`)

Para gerenciar o ambiente de desenvolvimento, homologação e produção, o `eas.json` possui três perfis principais:

### 1. Perfil `preview` (Gera o arquivo APK para instalação direta)
Ideal para compartilhar com o cliente piloto ou instalar em emuladores e aparelhos físicos de teste sem passar pela Play Store.
* **Comando para gerar na nuvem da Expo:**
  ```bash
  cd mobile
  npx eas-cli@latest build --platform android --profile preview
  ```

### 2. Perfil `production` (Gera o arquivo AAB para a Play Store)
Prepara o pacote otimizado final e assinado para ser enviado diretamente para o console de desenvolvedor do Google Play.
* **Comando para gerar na nuvem da Expo:**
  ```bash
  cd mobile
  npx eas-cli@latest build --platform android --profile production
  ```

### 3. Perfil `development` (Build de desenvolvimento nativo)
Gera um executável de testes para desenvolvimento com hot-reload ativo.
* **Comando para gerar:**
  ```bash
  cd mobile
  npx eas-cli@latest build --platform android --profile development
  ```

---

## 🌐 Injeção de Variáveis de Ambiente no Build (`EXPO_PUBLIC_API_BASE_URL`)

Para o aplicativo de produção falar com a API de backend correta (e não `localhost`), você precisa definir a URL pública do backend durante o build.

### Opção A: Definir no `eas.json` (Recomendada para agilidade)
Você pode adicionar o bloco `"env"` diretamente no perfil desejado no seu arquivo `eas.json`:

```json
{
  "build": {
    "preview": {
      "android": {
        "buildType": "apk"
      },
      "env": {
        "EXPO_PUBLIC_API_BASE_URL": "https://geoadmin-pro-api-njpsk7knsa-rj.a.run.app"
      }
    },
    "production": {
      "env": {
        "EXPO_PUBLIC_API_BASE_URL": "https://geoadmin-pro-api-njpsk7knsa-rj.a.run.app"
      }
    }
  }
}
```

### Opção B: Definir via Linha de Comando (EAS Secrets)
Para chaves sensíveis que não devem ficar no repositório Git, você pode configurar o segredo no painel da Expo ou injetar no comando de build:
```bash
EXPO_PUBLIC_API_BASE_URL="https://SuaUrlApiReal.app" npx eas-cli@latest build --platform android --profile preview
```

---

## 📲 Execução e Desenvolvimento Local

Para rodar localmente no seu computador durante o desenvolvimento:

* **Iniciar o Metro Bundler na Web (Visualização rápida no Navegador):**
  ```bash
  cd mobile
  npm run web
  ```
  *(Acessível em `http://localhost:8081`)*

* **Iniciar o Metro Bundler no Emulador Android:**
  ```bash
  cd mobile
  npx expo start --android
  ```

* **Build Nativo Local (Caso precise debugar componentes nativos como Bluetooth):**
  ```bash
  cd mobile
  npx expo run:android
  ```

---

## 📈 Resolução de Problemas Comuns

1. **Erro de Keystore no Android:**
   Ao rodar o `eas build` pela primeira vez, ele perguntará se deseja que a Expo gerencie a sua chave de assinatura (Keystore). Selecione **Sim (Yes)** para que a Expo crie e salve a chave de forma segura no painel web.
2. **Falha na porta 8081:**
   Se disser que a porta 8081 já está em uso por outro Metro, use o comando para matar processos antigos do node ou libere a porta:
   ```powershell
   Stop-Process -Name "node" -Force -ErrorAction SilentlyContinue
   ```
