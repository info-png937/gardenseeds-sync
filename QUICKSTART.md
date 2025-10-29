# ⚡ GUÍA RÁPIDA - 15 MINUTOS

## 🎯 RESUMEN

Sistema automático que sincroniza pedidos de GardenSeeds cada 4 horas usando GitHub Actions (gratis).

```
GitHub Actions → Extrae pedidos → Guarda JSON → PrestaShop lee JSON
```

---

## 📋 INSTALACIÓN RÁPIDA

### ✅ PARTE 1: GitHub (10 minutos)

1. **Crear repo:**
   - https://github.com/new
   - Nombre: `gardenseeds-sync`
   - Público o Privado
   - Crear

2. **Subir archivos:**
   ```bash
   cd gardenseeds-sync-github/
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/TU_USUARIO/gardenseeds-sync.git
   git push -u origin main
   ```

3. **Añadir secrets:**
   - Settings → Secrets → Actions → New secret
   - `GARDENSEEDS_USER` = `EUROGROW`
   - `GARDENSEEDS_PASS` = `Eurogrow1234`

4. **Activar Actions:**
   - Actions → Enable workflows
   - Run workflow → Run workflow
   - Esperar 2-3 min
   - ✅ Verificar que `pedidos_latest.json` se creó

---

### ✅ PARTE 2: PrestaShop (5 minutos)

1. **Actualizar módulo:**
   - Subir `gardenseedspedidos.php` actualizado
   - Ubicación: `/modules/gardenseedspedidos/`

2. **Configurar URL GitHub:**
   
   Editar línea 10 en `gardenseedspedidos.php`:
   
   **Si repo PÚBLICO:**
   ```php
   const GITHUB_JSON_URL = 'https://raw.githubusercontent.com/TU_USUARIO/gardenseeds-sync/main/pedidos_latest.json';
   ```
   
   **Si repo PRIVADO:**
   ```php
   const GITHUB_JSON_URL = 'https://raw.githubusercontent.com/TU_USUARIO/gardenseeds-sync/main/pedidos_latest.json';
   const GITHUB_TOKEN = 'ghp_XXXXX'; // Token desde GitHub
   ```

3. **Probar:**
   - Backoffice → Módulos → GardenSeeds → Configurar
   - Sincronizar ahora
   - ✅ Debe mostrar: "Sincronización completada"

---

## 🎉 ¡LISTO!

Ahora cada 4 horas:
1. GitHub Actions extrae pedidos
2. Guarda JSON en GitHub
3. PrestaShop lo lee automáticamente

---

## 📊 MONITOREO

- **Ver ejecuciones:** https://github.com/TU_USUARIO/gardenseeds-sync/actions
- **Ver JSON actual:** https://raw.githubusercontent.com/TU_USUARIO/gardenseeds-sync/main/pedidos_latest.json
- **Logs PrestaShop:** `/modules/gardenseedspedidos/logs/sync.log`

---

## ⚙️ CONFIGURACIÓN

### Cambiar frecuencia

Editar `.github/workflows/sync.yml` línea 5:

```yaml
# Cada 6 horas:
- cron: '0 */6 * * *'

# Cada día a las 09:00:
- cron: '0 9 * * *'

# Cada hora:
- cron: '0 * * * *'
```

---

## 🆘 PROBLEMAS COMUNES

### ❌ GitHub Action falla

**Ver logs:**
- Actions → Click en ejecución fallida → View logs

**Solución:**
- Verificar secrets (GARDENSEEDS_USER, GARDENSEEDS_PASS)
- Re-run workflow

### ❌ PrestaShop: "Error descargando JSON"

**Solución:**
1. Verificar URL en línea 10
2. Repo privado → Añadir GITHUB_TOKEN
3. Verificar que `pedidos_latest.json` existe en GitHub

### ❌ No actualiza productos

**Solución:**
```sql
-- Verificar reference6
SHOW COLUMNS FROM ps_pspedidosproveedor LIKE 'reference6';

-- Añadir referencias
UPDATE ps_pspedidosproveedor 
SET reference6 = 'ABC123' 
WHERE id_product = 789;
```

---

## 💰 COSTE

**GRATIS** - GitHub Actions free tier: 2000 min/mes
- Uso real: ~240 min/mes (12%)

---

## 📞 AYUDA

- **README completo:** Ver `README.md` en el ZIP
- **Logs GitHub:** https://github.com/TU_USUARIO/gardenseeds-sync/actions
- **Logs PrestaShop:** `/modules/gardenseedspedidos/logs/`

---

**¡Todo listo en 15 minutos!** 🚀
