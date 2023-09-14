for name in "matplotlib" "TesseractOCR" "tiktoken" "ResumeReview" "PromotedAnswer" "MeguminWizardEx"; do modal deploy --name "$name" bot_"$name".py; done
