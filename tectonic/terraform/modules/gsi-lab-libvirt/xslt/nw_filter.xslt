<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

<xsl:template match="interface[@type='network']">
    <xsl:copy>
        <xsl:apply-templates select="@*|node()"/>
        <!-- Get network name -->
        <xsl:variable name="network_name" select="source/@network"/>
        <!-- Get vm name -->
        <xsl:variable name="vm_name" select="/domain/name"/>
        <!-- Attach nw filter -->
        <xsl:if test="not(contains($network_name, 'external'))">
            <filterref filter="{$vm_name}-{$network_name}"/>
        </xsl:if>
    </xsl:copy>
</xsl:template>

</xsl:stylesheet>