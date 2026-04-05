declare module "react-highlight-words" {
  import { ComponentType } from "react";

  interface HighlighterProps {
    searchWords: string[];
    textToHighlight: string;
    autoEscape?: boolean;
    highlightClassName?: string;
    highlightStyle?: React.CSSProperties;
    unhighlightClassName?: string;
    unhighlightStyle?: React.CSSProperties;
    caseSensitive?: boolean;
    sanitize?: (text: string) => string;
    findChunks?: (options: object) => object[];
    highlightTag?: string | ComponentType<any>;
    activeIndex?: number;
    activeClassName?: string;
    activeStyle?: React.CSSProperties;
  }

  const Highlighter: ComponentType<HighlighterProps>;
  export default Highlighter;
}
