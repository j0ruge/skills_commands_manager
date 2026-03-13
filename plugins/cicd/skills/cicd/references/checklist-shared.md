# Checklist Compartilhado — Infra CI/CD

Seções compartilhadas entre backend e frontend para configuração de novo environment.

---

## 1. Self-Hosted Runner

- [ ] Runner instalado e rodando como serviço: `sudo systemctl status actions.runner.*`
- [ ] Runner com label correto: `staging` ou `production`
- [ ] Runner aparece como "Online" em GitHub > Settings > Actions > Runners
- [ ] Docker instalado e acessível pelo runner user
- [ ] Runner user no grupo `docker` (evita problemas sudo/user)
- [ ] Runner user tem permissão para `docker compose`
- [ ] Labels verificados em GitHub > Settings > Actions > Runners
- [ ] GHCR auth configurado no mesmo contexto (user/sudo) que executa `docker pull`: `docker login ghcr.io`

**Instalação do runner:**

```bash
mkdir -p /opt/actions-runner && cd /opt/actions-runner
curl -o actions-runner-linux-x64-2.321.0.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.321.0/actions-runner-linux-x64-2.321.0.tar.gz
tar xzf actions-runner-linux-x64-2.321.0.tar.gz
./config.sh --url https://github.com/JRC-Brasil --token <ORG_TOKEN> --labels <staging|production>
sudo ./svc.sh install && sudo ./svc.sh start
```

---

## 2. GHCR / Imagens

- [ ] Visibilidade do package é **Private** (herda do repo)
- [ ] `GITHUB_TOKEN` tem permissão `packages: write` no workflow
- [ ] Tags de imagem corretas: `staging` para develop, `v*` + `latest` para produção

Verificar em: `github.com/orgs/JRC-Brasil/packages`

---

## 3. DNS e SSL

- [ ] DNS do domínio resolve para o IP do servidor: `dig dominio +short`
- [ ] Porta 80 acessível externamente (HTTP-01 challenge do Let's Encrypt)
- [ ] nginx-proxy + acme-companion rodando no servidor
- [ ] Certificado SSL via Let's Encrypt (`LETSENCRYPT_HOST` configurado)

---

## 4. Rede nginx-proxy (Base)

- [ ] Rede Docker do nginx-proxy existe no servidor: `docker network ls | grep proxy`
- [ ] nginx-proxy container está rodando
- [ ] `VIRTUAL_HOST` configurado no DNS (ou `/etc/hosts` para teste)
- [ ] `NGINX_NETWORK_NAME` secret corresponde ao nome exato da rede
