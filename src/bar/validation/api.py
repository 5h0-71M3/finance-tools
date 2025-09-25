# performs the validations
from src.bar.validation.reports import (
    validate_allianz,
    validate_ascot,
    validate_chaucer,
    validate_fortegra,
    validate_hartford,
    validate_hdi,
    # validates Lloyds Canada and UK
    validate_lloyds,
    validate_lloyds_er,
    validate_lloyds_us,
    validate_msig,
    validate_swissre,
    validate_vantage,
)

# todo add Aspen Validations

from src.bar.validation.carriers import (
    # Generic Validation Classes
    BasicValidation,  # used for HDI, Hartford
    AustraliaValidation,  # used for Allianz Australia and MSIG
    BasicValidationUS,  # used for Ascot
    # Carrier Validations
    AllianzBasicValidation,  # used for Allianz Germany, UK, Nordics
    AllianzUSValidation,  # used for Allianz US
    AllianzUKValidation,  # used for Allianz UK
    ChaucerValidation,  # used for the Chaucer validation,
    FortegraValidation,   # For Fortegra Validation
    LloydsValidation,  # For Lloyds Validation
    LloydsUnitedStatesValidation,  # for Lloyds US
    LloydsExecutiveRiskValidation,  # used for Lloyds ER
    SwissReValidation,  # used for all SwissRe (CAD, USD, Surplus, Admitted)
    VantageValidation,  # used for VantageValidation
)

# Daily Checks
# from src.pipeline_v2.validation import DailyValidation

__all__ = [
    "validate_allianz",
    "validate_ascot",
    "validate_chaucer",
    "validate_fortegra",
    "validate_hartford",
    "validate_hdi",
    "validate_lloyds",
    "validate_lloyds_er",
    "validate_lloyds_us",
    "validate_msig",
    "validate_swissre",
    "validate_vantage",
    "BasicValidation",
    "AustraliaValidation",
    "BasicValidationUS",
    "AllianzBasicValidation",
    "AllianzUSValidation",
    "AllianzUKValidation",
    "ChaucerValidation",
    "FortegraValidation",
    "LloydsValidation",
    "LloydsUnitedStatesValidation",
    "LloydsExecutiveRiskValidation",
    "SwissReValidation",
    "VantageValidation",
]
