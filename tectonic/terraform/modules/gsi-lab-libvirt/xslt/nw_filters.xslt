<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:output method="xml" indent="yes"/>
    
    <xsl:template match="@*|node()">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
    </xsl:template>
    
    <xsl:template match="//interface[@type='network']">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()"/>
            <!-- Obtener el nombre de la red desde el source network -->
            <xsl:variable name="network_name" select="source/@network"/>
            <!-- Crear el nombre del filter: sg-{vm_name}-{network_name} -->
            <xsl:variable name="vm_name" select="../../name"/>
            <xsl:if test="not(contains($network_name, 'external'))">
                <filterref filter="{$vm_name}-{$network_name}"/>
            </xsl:if>
        </xsl:copy>
    </xsl:template>
</xsl:stylesheet>