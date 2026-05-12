"use client";

import { Languages } from "lucide-react";
import {
  LanguageSelect,
  LanguageSelectText,
} from "fumadocs-ui/layouts/shared/slots/language-select";

type LanguageSwitcherProps = {
  className?: string;
};

const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({ className }) => {
  return (
    <LanguageSelect
      className={className}
      variant="outline"
      aria-label="Switch language"
    >
      <Languages aria-hidden="true" />
      <LanguageSelectText className="hidden text-xs md:inline" />
    </LanguageSelect>
  );
};

export default LanguageSwitcher;
