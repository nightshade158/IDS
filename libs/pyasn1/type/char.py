# ASN.1 "character string" types
from libs.pyasn1.type import univ, tag

class UTF8String(univ.OctetString):
    tagSet = univ.OctetString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 12)
        )
    encoding = "utf-8"

class NumericString(univ.OctetString):
    tagSet = univ.OctetString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 18)
        )

class PrintableString(univ.OctetString):
    tagSet = univ.OctetString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 19)
        )

class TeletexString(univ.OctetString):
    tagSet = univ.OctetString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 20)
        )
    

class VideotexString(univ.OctetString):
    tagSet = univ.OctetString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 21)
        )

class IA5String(univ.OctetString):
    tagSet = univ.OctetString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 22)
        )

class GraphicString(univ.OctetString):
    tagSet = univ.OctetString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 25)
        )

class VisibleString(univ.OctetString):
    tagSet = univ.OctetString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 26)
        )

class GeneralString(univ.OctetString):
    tagSet = univ.OctetString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 27)
        )

class UniversalString(univ.OctetString):
    tagSet = univ.OctetString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 28)
        )
    encoding = "utf-32-be"

class BMPString(univ.OctetString):
    tagSet = univ.OctetString.tagSet.tagImplicitly(
        tag.Tag(tag.tagClassUniversal, tag.tagFormatSimple, 30)
        )
    encoding = "utf-16-be"
