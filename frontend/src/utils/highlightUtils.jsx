import React from "react";

/**
 * Utility functions for highlighting search terms in text
 */

/**
 * Removes diacritics from a string (e.g., "café" -> "cafe")
 */
const removeDiacritics = (str) => {
  if (!str) return "";
  return str.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
};

/**
 * Highlights search terms in text with a clean styling approach
 * Supports non-ordered term searches (e.g., "B A" will highlight both B and A)
 * Returns an array of React nodes with matched text wrapped in <mark> elements
 * 
 * @param {string} text - The text to highlight
 * @param {string} searchTerm - The term to search for (can contain multiple words)
 * @param {boolean} ignoreDiacritics - Whether to ignore diacritics in matching
 * @returns {React.ReactNode[]} - Array of text and mark elements
 */
export const getHighlightedText = (text, searchTerm, ignoreDiacritics = false) => {
  if (!text || !searchTerm) {
    return [text];
  }

  const textStr = String(text);
  const searchStr = String(searchTerm).trim();

  if (!searchStr) {
    return [textStr];
  }

  let compareText = textStr;
  let searchTerms = searchStr.split(/\s+/); // Split by whitespace to handle multiple terms

  if (ignoreDiacritics) {
    compareText = removeDiacritics(textStr);
    searchTerms = searchTerms.map(term => removeDiacritics(term));
  }

  // Build regex to match any of the search terms (non-ordered search)
  const escapedTerms = searchTerms.map(term => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const regex = new RegExp(`(${escapedTerms.join("|")})`, "gi");
  
  if (!regex.test(compareText)) {
    return [textStr];
  }

  // Reset regex lastIndex after test
  regex.lastIndex = 0;

  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(compareText)) !== null) {
    const startIndex = match.index;
    const endIndex = match.index + match[0].length;

    // Add text before match
    if (startIndex > lastIndex) {
      parts.push(textStr.substring(lastIndex, startIndex));
    }

    // Add highlighted match (using original text, not normalized)
    parts.push(
      <mark key={`highlight-${startIndex}`} className="search-highlight">
        {textStr.substring(startIndex, endIndex)}
      </mark>
    );

    lastIndex = endIndex;
  }

  // Add remaining text
  if (lastIndex < textStr.length) {
    parts.push(textStr.substring(lastIndex));
  }

  return parts;
};

/**
 * Get which fields should be highlighted based on search parameters
 * 
 * @param {Object} searchParams - The current search parameters
 * @returns {Set} - Set of field names that should be highlighted
 */
export const getSearchableFields = (searchParams) => {
  const fields = new Set();

  if (searchParams.searchByCodPedc) fields.add("cod_pedc");
  if (searchParams.searchByFornecedor) fields.add("fornecedor_descricao");
  if (searchParams.searchByCnpjFornecedor) fields.add("fornecedor_id");
  if (searchParams.searchByObservacao) fields.add("observacao");
  if (searchParams.searchByItemId) fields.add("item_id");
  if (searchParams.searchByDescricao) fields.add("descricao");
  if (searchParams.searchByNumNF) fields.add("num_nf");

  return fields;
};

/**
 * Determines if a field should be highlighted based on enhanced search mode
 */
export const shouldHighlightField = (fieldName, searchParams, usingEnhanced) => {
  // Map display field names to search parameter names
  const fieldMapping = {
    "cod_pedc": "searchByCodPedc",
    "fornecedor_descricao": "searchByFornecedor",
    "fornecedor_id": "searchByCnpjFornecedor",
    "observacao": "searchByObservacao",
    "item_id": "searchByItemId",
    "descricao": "searchByDescricao",
    "num_nf": "searchByNumNF",
  };

  const paramName = fieldMapping[fieldName];
  if (!paramName) {
    return false;
  }

  // Check if the corresponding search parameter is enabled
  return searchParams[paramName] === true;
};
