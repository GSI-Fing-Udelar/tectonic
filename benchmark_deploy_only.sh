#!/bin/bash
# Script para medir solo el tiempo de despliegue de Moodle (sin crear imágenes)
# Uso: ./benchmark_deploy_only.sh
# Requiere que la imagen base de Moodle ya esté creada

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuración
CONFIG_FILE="tectonic.ini"
LAB_EDITION="examples/moodle_minimal.yml"
LOG_FILE="moodle_deploy_benchmark_$(date +%Y%m%d_%H%M%S).log"

# Función para imprimir con timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Función para imprimir sección
section() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    log "=== $1 ==="
}

# Banner inicial
echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     Benchmark de Despliegue de Moodle (Solo Deploy)       ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

log "Iniciando benchmark de despliegue (sin crear imágenes)"
log "Config: $CONFIG_FILE"
log "Lab Edition: $LAB_EDITION"

# Variables para almacenar tiempos
CLEANUP_TIME=0
DEPLOY_TIME=0
TOTAL_TIME=0

# 1. Limpieza
section "1. Limpieza de despliegue anterior"
start_cleanup=$(date +%s)
echo -e "${YELLOW}⏳ Limpiando despliegue anterior...${NC}"
if poetry run tectonic --config "$CONFIG_FILE" "$LAB_EDITION" destroy \
    --machines \
    --moodle \
    --force 2>&1 | tee -a "$LOG_FILE"; then
    end_cleanup=$(date +%s)
    CLEANUP_TIME=$((end_cleanup - start_cleanup))
    log "Limpieza completada en ${CLEANUP_TIME}s"
    echo -e "${GREEN}✅ Limpieza completada en ${CLEANUP_TIME}s${NC}"
else
    log "Limpieza falló o no había nada que limpiar"
    CLEANUP_TIME=0
    echo -e "${YELLOW}⚠️  No había nada que limpiar${NC}"
fi

# 2. Despliegue
section "2. Despliegue de Moodle"
start_deploy=$(date +%s)
log "Iniciando despliegue de Moodle"
echo -e "${YELLOW}⏳ Ejecutando despliegue de Moodle...${NC}"
echo -e "${YELLOW}   (Esto puede tomar varios minutos)${NC}"

if poetry run tectonic --config "$CONFIG_FILE" "$LAB_EDITION" deploy \
    --force 2>&1 | tee -a "$LOG_FILE"; then
    end_deploy=$(date +%s)
    DEPLOY_TIME=$((end_deploy - start_deploy))
    minutes=$((DEPLOY_TIME / 60))
    seconds=$((DEPLOY_TIME % 60))
    
    log "Despliegue completado en ${minutes}m ${seconds}s"
    echo -e "${GREEN}✅ Despliegue completado en ${minutes}m ${seconds}s${NC}"
else
    echo -e "${RED}❌ Error en el despliegue${NC}"
    exit 1
fi

# Calcular tiempo total
TOTAL_TIME=$((CLEANUP_TIME + DEPLOY_TIME))

# 3. Obtener información
section "3. Obteniendo información del despliegue"
poetry run tectonic --config "$CONFIG_FILE" "$LAB_EDITION" info 2>&1 | tee -a "$LOG_FILE"

# 4. Resumen final
section "Resumen de Tiempos"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                    RESULTADOS DEL BENCHMARK                ${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Función para formatear tiempo
format_time() {
    local seconds=$1
    local minutes=$((seconds / 60))
    local secs=$((seconds % 60))
    if [ $minutes -gt 0 ]; then
        echo "${minutes}m ${secs}s"
    else
        echo "${secs}s"
    fi
}

echo -e "${CYAN}Limpieza:${NC}     $(format_time $CLEANUP_TIME)"
echo -e "${CYAN}Despliegue:${NC}   $(format_time $DEPLOY_TIME)"
echo -e "${CYAN}───────────────────────────────────────────────────────────${NC}"
echo -e "${GREEN}Tiempo total:${NC} $(format_time $TOTAL_TIME)"
echo ""

# Guardar resumen en log
log "═══════════════════════════════════════════════════════════"
log "RESUMEN DE TIEMPOS:"
log "  Limpieza:     $(format_time $CLEANUP_TIME)"
log "  Despliegue:   $(format_time $DEPLOY_TIME)"
log "  ───────────────────────────────────────────────────────"
log "  Tiempo total: $(format_time $TOTAL_TIME)"
log "═══════════════════════════════════════════════════════════"

echo -e "${GREEN}✅ Benchmark de despliegue completado exitosamente${NC}"
echo -e "${CYAN}📄 Log guardado en: $LOG_FILE${NC}"
echo ""

# Mostrar información de acceso
echo -e "${YELLOW}💡 Para obtener credenciales y URL de acceso:${NC}"
echo "   poetry run tectonic --config $CONFIG_FILE $LAB_EDITION info"
echo ""

