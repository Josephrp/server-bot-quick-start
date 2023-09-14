for name in "upload" "exec"; do modal deploy helper_"$name".py; done
for name in "matplotlib" "TesseractOCR" "tiktoken" "ResumeReview" "PromotedAnswer" "MeguminWizardEx"; do modal deploy --name "$name" bot_"$name".py; done
