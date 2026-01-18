<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    
    <xsl:template match="@*|node()">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
    </xsl:template>

    <xsl:include href="${nw_filter_path}"/>

    %{ if custom_path != "/dev/null" }
    <xsl:include href="${custom_path}"/>
    %{ endif }
    
</xsl:stylesheet>