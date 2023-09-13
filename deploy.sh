for name in "TesseractOCR" "tiktoken" "ResumeReview" "PromotedAnswer" "MeguminWizardEx"; do modal deploy --name "$name" "$name"_bot.py; done
