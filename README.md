# 🌱 GardenSeeds Sync con GitHub Actions

Sistema automático de sincronización de pedidos de GardenSeeds usando GitHub Actions + Playwright.

## 🎯 Cómo funciona

```
┌──────────────────┐
│ GitHub Actions   │ ← Ejecuta cada 4 horas (gratis)
│ + Playwright     │ ← Login + Extrae pedidos
└────────┬─────────┘
         │
         ↓ Guarda JSON
┌──────────────────┐
│ GitHub Repo      │ ← pedidos_latest.json (público)
│ (Este repo)      │
└────────┬─────────┘
         │
         ↓ Descarga
┌──────────────────┐
│ PrestaShop       │ ← Módulo PHP lee JSON
│ (Tu servidor)    │ ← Actualiza BD
└──────────────────┘
```

---

## 📋 SETUP - Parte 1: GitHub

### PASO 1: Crear repositorio

1. Ir a: https://github.com/new
2. Nombre: `gardenseeds-sync`
3. **Visibilidad:** Público (para raw URLs) o Privado (con token)
4. Crear repositorio

### PASO 2: Subir archivos

```bash
# Clonar el repo
git clone https://github.com/TU_USUARIO/gardenseeds-sync.git
cd gardenseeds-sync

# Copiar archivos de este ZIP
cp -r .github gardenseeds_extractor.py README.md .

# Commit inicial
git add .
git commit -m "Initial commit"
git push
```

### PASO 3: Configurar Secrets

1. Ir a: **Settings → Secrets and variables → Actions**
2. Click: **New repository secret**
3. Añadir estos secrets:

```
Name: GARDENSEEDS_USER
Value: EUROGROW

Name: GARDENSEEDS_PASS  
Value: Eurogrow1234
```

### PASO 4: Activar GitHub Actions

1. Ir a: **Actions** (pestaña superior)
2. Click: **I understand my workflows, go ahead and enable them**
3. Verificar que aparece: **Sync GardenSeeds Pedidos**

### PASO 5: Primera ejecución manual

1. Click en workflow: **Sync GardenSeeds Pedidos**
2. Click: **Run workflow** (botón derecho)
3. Click: **Run workflow** (confirmar)
4. Esperar 2-3 minutos
5. Verificar: ✅ Success

Si funciona, verás:
- `pedidos_latest.json` creado en el repo
- Carpeta `pedidos/` con históricos

---

## 📋 SETUP - Parte 2: PrestaShop

### PASO 1: Actualizar módulo

Reemplazar archivo en servidor:
```
/var/www/vhosts/eurogrow.es/httpdocs/modules/gardenseedspedidos/gardenseedspedidos.php
```

Con el archivo incluido: `gardenseedspedidos_github.php`

### PASO 2: Configurar URL de GitHub

Editar en `gardenseedspedidos.php` línea ~50:

**Si repo es PÚBLICO:**
```php
const GITHUB_JSON_URL = 'https://raw.githubusercontent.com/TU_USUARIO/gardenseeds-sync/main/pedidos_latest.json';
```

**Si repo es PRIVADO:**
```php
const GITHUB_JSON_URL = 'https://raw.githubusercontent.com/TU_USUARIO/gardenseeds-sync/main/pedidos_latest.json';
const GITHUB_TOKEN = 'ghp_XXXXXXXXXXXXX'; // Personal Access Token
```

Para crear token privado:
1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token
3. Scope: `repo` (Full control)
4. Copiar token

### PASO 3: Probar desde PrestaShop

1. Backoffice → **Módulos → GardenSeeds Pedidos → Configurar**
2. Click: **Sincronizar ahora**
3. Debe mostrar: "Sincronización completada"

---

## ⏰ PROGRAMACIÓN AUTOMÁTICA

El workflow se ejecuta automáticamente:

```yaml
schedule:
  - cron: '0 */4 * * *'  # Cada 4 horas
```

**Horarios UTC:**
- 00:00 → 01:00 CET
- 04:00 → 05:00 CET  
- 08:00 → 09:00 CET
- 12:00 → 13:00 CET
- 16:00 → 17:00 CET
- 20:00 → 21:00 CET

**Cambiar frecuencia:**
```yaml
# Cada 6 horas:
- cron: '0 */6 * * *'

# Cada día a las 09:00 UTC (10:00 CET):
- cron: '0 9 * * *'

# Cada hora:
- cron: '0 * * * *'
```

---

## 📊 MONITOREO

### Ver ejecuciones:
https://github.com/TU_USUARIO/gardenseeds-sync/actions

### Ver último JSON:
https://raw.githubusercontent.com/TU_USUARIO/gardenseeds-sync/main/pedidos_latest.json

### Ver histórico:
https://github.com/TU_USUARIO/gardenseeds-sync/tree/main/pedidos

---

## 🔍 TROUBLESHOOTING

### ❌ Action falla con "Login falló"

**Causa:** Credenciales incorrectas

**Solución:**
1. Settings → Secrets → Actions
2. Verificar `GARDENSEEDS_USER` y `GARDENSEEDS_PASS`
3. Re-run workflow

### ❌ PrestaShop: "Error descargando JSON"

**Causa:** URL incorrecta o repo privado sin token

**Solución:**
1. Verificar URL en `gardenseedspedidos.php`
2. Si repo privado, añadir `GITHUB_TOKEN`
3. Verificar que `pedidos_latest.json` existe en GitHub

### ❌ No encuentra productos

**Causa:** `reference6` no configurado

**Solución:**
```sql
-- Verificar reference6 existe
SHOW COLUMNS FROM ps_pspedidosproveedor LIKE 'reference6';

-- Añadir referencias de GardenSeeds
UPDATE ps_pspedidosproveedor 
SET reference6 = 'ABC123' 
WHERE id_product = 789;
```

---

## 📁 ESTRUCTURA DEL REPO

```
gardenseeds-sync/
├── .github/
│   └── workflows/
│       └── sync.yml              ← GitHub Actions workflow
├── gardenseeds_extractor.py      ← Script Python + Playwright
├── pedidos_latest.json           ← Último resultado (actualizado automáticamente)
├── pedidos/
│   ├── pedidos_2025-10-29.json  ← Históricos (por fecha)
│   └── pedidos_2025-10-28.json
└── README.md                     ← Este archivo
```

---

## 💰 COSTES

**GitHub Actions:**
- ✅ **GRATIS** hasta 2000 minutos/mes
- Cada ejecución: ~2 minutos
- 4 ejecuciones/día × 30 días = 240 min/mes
- **Uso:** 12% del límite gratuito

**GitHub Storage:**
- ✅ **GRATIS** (archivos JSON pequeños)

**Total:** **$0/mes** ✅

---

## ✅ VENTAJAS

✅ **100% Automático** - Sin intervención manual  
✅ **Gratis** - GitHub Actions free tier  
✅ **Sin dependencias** - Tu servidor solo necesita PHP  
✅ **Logs públicos** - Ver ejecuciones en GitHub  
✅ **Histórico** - Git guarda todos los pedidos  
✅ **Robusto** - Playwright maneja JavaScript  
✅ **Escalable** - Fácil añadir más proveedores  

---

## 📞 SOPORTE

- **GitHub Actions logs:** https://github.com/TU_USUARIO/gardenseeds-sync/actions
- **JSON actual:** https://raw.githubusercontent.com/TU_USUARIO/gardenseeds-sync/main/pedidos_latest.json
- **Módulo PrestaShop:** `/modules/gardenseedspedidos/logs/`

---

**Versión:** 1.0.0  
**Fecha:** Octubre 2025  
**Autor:** Eurogrow
