# BER decoder
from libs.pyasn1 import debug, error
from libs.pyasn1.codec.ber import eoo
from libs.pyasn1.compat.octets import oct2int, isOctetsType
from libs.pyasn1.type import tag, univ, char, useful, tagmap


class AbstractDecoder:
    protoComponent = None
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                     length, state, decodeFun, substrateFun):
        raise error.PyAsn1Error('Decoder not implemented for %s' % (tagSet,))

    def indefLenValueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                     length, state, decodeFun, substrateFun):
        raise error.PyAsn1Error('Indefinite length mode decoder not implemented for %s' % (tagSet,))

class AbstractSimpleDecoder(AbstractDecoder):
    tagFormats = (tag.tagFormatSimple,)
    def _createComponent(self, asn1Spec, tagSet, value=None):
        if tagSet[0][1] not in self.tagFormats:
            raise error.PyAsn1Error('Invalid tag format %r for %r' % (tagSet[0], self.protoComponent,))
        if asn1Spec is None:
            return self.protoComponent.clone(value, tagSet)
        elif value is None:
            return asn1Spec
        else:
            return asn1Spec.clone(value)
        
class AbstractConstructedDecoder(AbstractDecoder):
    tagFormats = (tag.tagFormatConstructed,)
    def _createComponent(self, asn1Spec, tagSet, value=None):
        if tagSet[0][1] not in self.tagFormats:
            raise error.PyAsn1Error('Invalid tag format %r for %r' % (tagSet[0], self.protoComponent,))
        if asn1Spec is None:
            return self.protoComponent.clone(tagSet)
        else:
            return asn1Spec.clone()
                                
class EndOfOctetsDecoder(AbstractSimpleDecoder):
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                     length, state, decodeFun, substrateFun):
        return eoo.endOfOctets, substrate[length:]

class ExplicitTagDecoder(AbstractSimpleDecoder):
    protoComponent = univ.Any('')
    tagFormats = (tag.tagFormatConstructed,)
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                     length, state, decodeFun, substrateFun):
        if substrateFun:
            return substrateFun(
                       self._createComponent(asn1Spec, tagSet, ''),
                       substrate, length
                   )
        head, tail = substrate[:length], substrate[length:]
        value, _ = decodeFun(head, asn1Spec, tagSet, length)
        return value, tail

    def indefLenValueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                             length, state, decodeFun, substrateFun):
        if substrateFun:
            return substrateFun(
                       self._createComponent(asn1Spec, tagSet, ''),
                       substrate, length
                   )
        value, substrate = decodeFun(substrate, asn1Spec, tagSet, length)
        terminator, substrate = decodeFun(substrate)
        if eoo.endOfOctets.isSameTypeWith(terminator) and \
                terminator == eoo.endOfOctets:
            return value, substrate
        else:
            raise error.PyAsn1Error('Missing end-of-octets terminator')

explicitTagDecoder = ExplicitTagDecoder()

class IntegerDecoder(AbstractSimpleDecoder):
    protoComponent = univ.Integer(0)
    precomputedValues = {
        '\x00':  0,
        '\x01':  1,
        '\x02':  2,
        '\x03':  3,
        '\x04':  4,
        '\x05':  5,
        '\x06':  6,
        '\x07':  7,
        '\x08':  8,
        '\x09':  9,
        '\xff': -1,
        '\xfe': -2,
        '\xfd': -3,
        '\xfc': -4,
        '\xfb': -5
        }
    
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet, length,
                     state, decodeFun, substrateFun):
        head, tail = substrate[:length], substrate[length:]
        if not head:
            return self._createComponent(asn1Spec, tagSet, 0), tail
        if head in self.precomputedValues:
            value = self.precomputedValues[head]
        else:
            firstOctet = oct2int(head[0])
            if firstOctet & 0x80:
                value = -1
            else:
                value = 0
            for octet in head:
                value = value << 8 | oct2int(octet)
        return self._createComponent(asn1Spec, tagSet, value), tail

class BooleanDecoder(IntegerDecoder):
    protoComponent = univ.Boolean(0)
    def _createComponent(self, asn1Spec, tagSet, value=None):
        return IntegerDecoder._createComponent(self, asn1Spec, tagSet, value and 1 or 0)

class BitStringDecoder(AbstractSimpleDecoder):
    protoComponent = univ.BitString(())
    tagFormats = (tag.tagFormatSimple, tag.tagFormatConstructed)
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet, length,
                     state, decodeFun, substrateFun):
        head, tail = substrate[:length], substrate[length:]
        if tagSet[0][1] == tag.tagFormatSimple:    # XXX what tag to check?
            if not head:
                raise error.PyAsn1Error('Empty substrate')
            trailingBits = oct2int(head[0])
            if trailingBits > 7:
                raise error.PyAsn1Error(
                    'Trailing bits overflow %s' % trailingBits
                    )
            head = head[1:]
            lsb = p = 0; l = len(head)-1; b = ()
            while p <= l:
                if p == l:
                    lsb = trailingBits
                j = 7                    
                o = oct2int(head[p])
                while j >= lsb:
                    b = b + ((o>>j)&0x01,)
                    j = j - 1
                p = p + 1
            return self._createComponent(asn1Spec, tagSet, b), tail
        r = self._createComponent(asn1Spec, tagSet, ())
        if substrateFun:
            return substrateFun(r, substrate, length)
        while head:
            component, head = decodeFun(head)
            r = r + component
        return r, tail

    def indefLenValueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                             length, state, decodeFun, substrateFun):
        r = self._createComponent(asn1Spec, tagSet, '')
        if substrateFun:
            return substrateFun(r, substrate, length)
        while substrate:
            component, substrate = decodeFun(substrate)
            if eoo.endOfOctets.isSameTypeWith(component) and \
                    component == eoo.endOfOctets:
                break
            r = r + component
        else:
            raise error.SubstrateUnderrunError(
                'No EOO seen before substrate ends'
                )
        return r, substrate

class OctetStringDecoder(AbstractSimpleDecoder):
    protoComponent = univ.OctetString('')
    tagFormats = (tag.tagFormatSimple, tag.tagFormatConstructed)
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet, length,
                     state, decodeFun, substrateFun):
        head, tail = substrate[:length], substrate[length:]
        if tagSet[0][1] == tag.tagFormatSimple:    # XXX what tag to check?
            return self._createComponent(asn1Spec, tagSet, head), tail
        r = self._createComponent(asn1Spec, tagSet, '')
        if substrateFun:
            return substrateFun(r, substrate, length)
        while head:
            component, head = decodeFun(head)
            r = r + component
        return r, tail

    def indefLenValueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                             length, state, decodeFun, substrateFun):
        r = self._createComponent(asn1Spec, tagSet, '')
        if substrateFun:
            return substrateFun(r, substrate, length)
        while substrate:
            component, substrate = decodeFun(substrate)
            if eoo.endOfOctets.isSameTypeWith(component) and \
                    component == eoo.endOfOctets:
                break
            r = r + component
        else:
            raise error.SubstrateUnderrunError(
                'No EOO seen before substrate ends'
                )
        return r, substrate

class NullDecoder(AbstractSimpleDecoder):
    protoComponent = univ.Null('')
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                     length, state, decodeFun, substrateFun):
        head, tail = substrate[:length], substrate[length:]
        r = self._createComponent(asn1Spec, tagSet)
        if head:
            raise error.PyAsn1Error('Unexpected %d-octet substrate for Null' % length)
        return r, tail

class ObjectIdentifierDecoder(AbstractSimpleDecoder):
    protoComponent = univ.ObjectIdentifier(())
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet, length,
                     state, decodeFun, substrateFun):
        head, tail = substrate[:length], substrate[length:]
        if not head:
            raise error.PyAsn1Error('Empty substrate')

        # Get the first subid
        subId = oct2int(head[0])
        oid = divmod(subId, 40)

        index = 1
        substrateLen = len(head)
        while index < substrateLen:
            subId = oct2int(head[index])
            index = index + 1
            if subId == 128:
                # ASN.1 spec forbids leading zeros (0x80) in sub-ID OID
                # encoding, tolerating it opens a vulnerability.
                # See http://www.cosic.esat.kuleuven.be/publications/article-1432.pdf page 7
                raise error.PyAsn1Error('Invalid leading 0x80 in sub-OID')
            elif subId > 128:
                # Construct subid from a number of octets
                nextSubId = subId
                subId = 0
                while nextSubId >= 128:
                    subId = (subId << 7) + (nextSubId & 0x7F)
                    if index >= substrateLen:
                        raise error.SubstrateUnderrunError(
                            'Short substrate for sub-OID past %s' % (oid,)
                            )
                    nextSubId = oct2int(head[index])
                    index = index + 1
                subId = (subId << 7) + nextSubId
            oid = oid + (subId,)
        return self._createComponent(asn1Spec, tagSet, oid), tail

class RealDecoder(AbstractSimpleDecoder):
    protoComponent = univ.Real()
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                     length, state, decodeFun, substrateFun):
        head, tail = substrate[:length], substrate[length:]
        if not head:
            return self._createComponent(asn1Spec, tagSet, 0.0), tail
        fo = oct2int(head[0]); head = head[1:]
        if fo & 0x80:  # binary enoding
            n = (fo & 0x03) + 1
            if n == 4:
                n = oct2int(head[0])
            eo, head = head[:n], head[n:]
            if not eo or not head:
                raise error.PyAsn1Error('Real exponent screwed')
            e = oct2int(eo[0]) & 0x80 and -1 or 0
            while eo:         # exponent
                e <<= 8
                e |= oct2int(eo[0])
                eo = eo[1:]
            p = 0
            while head:  # value
                p <<= 8
                p |= oct2int(head[0])
                head = head[1:]
            if fo & 0x40:    # sign bit
                p = -p
            value = (p, 2, e)
        elif fo & 0x40:  # infinite value
            value = fo & 0x01 and '-inf' or 'inf'
        elif fo & 0xc0 == 0:  # character encoding
            try:
                if fo & 0x3 == 0x1:  # NR1
                    value = (int(head), 10, 0)
                elif fo & 0x3 == 0x2:  # NR2
                    value = float(head)
                elif fo & 0x3 == 0x3:  # NR3
                    value = float(head)
                else:
                    raise error.SubstrateUnderrunError(
                        'Unknown NR (tag %s)' % fo
                        )
            except ValueError:
                raise error.SubstrateUnderrunError(
                    'Bad character Real syntax'
                    )
        else:
            raise error.SubstrateUnderrunError(
                'Unknown encoding (tag %s)' % fo
                )
        return self._createComponent(asn1Spec, tagSet, value), tail
        
class SequenceDecoder(AbstractConstructedDecoder):
    protoComponent = univ.Sequence()
    def _getComponentTagMap(self, r, idx):
        try:
            return r.getComponentTagMapNearPosition(idx)
        except error.PyAsn1Error:
            return

    def _getComponentPositionByType(self, r, t, idx):
        return r.getComponentPositionNearType(t, idx)
    
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                     length, state, decodeFun, substrateFun):
        head, tail = substrate[:length], substrate[length:]
        r = self._createComponent(asn1Spec, tagSet)
        idx = 0
        if substrateFun:
            return substrateFun(r, substrate, length)
        while head:
            asn1Spec = self._getComponentTagMap(r, idx)
            component, head = decodeFun(head, asn1Spec)
            idx = self._getComponentPositionByType(
                r, component.getEffectiveTagSet(), idx
                )
            r.setComponentByPosition(idx, component, asn1Spec is None)
            idx = idx + 1
        r.setDefaultComponents()
        r.verifySizeSpec()
        return r, tail

    def indefLenValueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                             length, state, decodeFun, substrateFun):
        r = self._createComponent(asn1Spec, tagSet)
        if substrateFun:
            return substrateFun(r, substrate, length)
        idx = 0
        while substrate:
            asn1Spec = self._getComponentTagMap(r, idx)
            component, substrate = decodeFun(substrate, asn1Spec)
            if eoo.endOfOctets.isSameTypeWith(component) and \
                    component == eoo.endOfOctets:
                break
            idx = self._getComponentPositionByType(
                r, component.getEffectiveTagSet(), idx
                )            
            r.setComponentByPosition(idx, component, asn1Spec is None)
            idx = idx + 1                
        else:
            raise error.SubstrateUnderrunError(
                'No EOO seen before substrate ends'
                )
        r.setDefaultComponents()
        r.verifySizeSpec()
        return r, substrate

class SequenceOfDecoder(AbstractConstructedDecoder):
    protoComponent = univ.SequenceOf()    
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                     length, state, decodeFun, substrateFun):
        head, tail = substrate[:length], substrate[length:]
        r = self._createComponent(asn1Spec, tagSet)
        if substrateFun:
            return substrateFun(r, substrate, length)
        asn1Spec = r.getComponentType()
        idx = 0
        while head:
            component, head = decodeFun(head, asn1Spec)
            r.setComponentByPosition(idx, component, asn1Spec is None)
            idx = idx + 1
        r.verifySizeSpec()
        return r, tail

    def indefLenValueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                             length, state, decodeFun, substrateFun):
        r = self._createComponent(asn1Spec, tagSet)
        if substrateFun:
            return substrateFun(r, substrate, length)
        asn1Spec = r.getComponentType()
        idx = 0
        while substrate:
            component, substrate = decodeFun(substrate, asn1Spec)
            if eoo.endOfOctets.isSameTypeWith(component) and \
                    component == eoo.endOfOctets:
                break
            r.setComponentByPosition(idx, component, asn1Spec is None)
            idx = idx + 1                
        else:
            raise error.SubstrateUnderrunError(
                'No EOO seen before substrate ends'
                )
        r.verifySizeSpec()
        return r, substrate

class SetDecoder(SequenceDecoder):
    protoComponent = univ.Set()
    def _getComponentTagMap(self, r, idx):
        return r.getComponentTagMap()

    def _getComponentPositionByType(self, r, t, idx):
        nextIdx = r.getComponentPositionByType(t)
        if nextIdx is None:
            return idx
        else:
            return nextIdx
    
class SetOfDecoder(SequenceOfDecoder):
    protoComponent = univ.SetOf()
    
class ChoiceDecoder(AbstractConstructedDecoder):
    protoComponent = univ.Choice()
    tagFormats = (tag.tagFormatSimple, tag.tagFormatConstructed)
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                     length, state, decodeFun, substrateFun):
        head, tail = substrate[:length], substrate[length:]
        r = self._createComponent(asn1Spec, tagSet)
        if substrateFun:
            return substrateFun(r, substrate, length)
        if r.getTagSet() == tagSet: # explicitly tagged Choice
            component, head = decodeFun(
                head, r.getComponentTagMap()
                )
        else:
            component, head = decodeFun(
                head, r.getComponentTagMap(), tagSet, length, state
                )
        if isinstance(component, univ.Choice):
            effectiveTagSet = component.getEffectiveTagSet()
        else:
            effectiveTagSet = component.getTagSet()
        r.setComponentByType(effectiveTagSet, component, 0, asn1Spec is None)
        return r, tail

    def indefLenValueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                     length, state, decodeFun, substrateFun):
        r = self._createComponent(asn1Spec, tagSet)
        if substrateFun:
            return substrateFun(r, substrate, length)
        if r.getTagSet() == tagSet: # explicitly tagged Choice
            component, substrate = decodeFun(substrate, r.getComponentTagMap())
            eooMarker, substrate = decodeFun(substrate)  # eat up EOO marker
            if not eoo.endOfOctets.isSameTypeWith(eooMarker) or \
                    eooMarker != eoo.endOfOctets:
                raise error.PyAsn1Error('No EOO seen before substrate ends')
        else:
            component, substrate= decodeFun(
                substrate, r.getComponentTagMap(), tagSet, length, state
            )
        if isinstance(component, univ.Choice):
            effectiveTagSet = component.getEffectiveTagSet()
        else:
            effectiveTagSet = component.getTagSet()
        r.setComponentByType(effectiveTagSet, component, 0, asn1Spec is None)
        return r, substrate

class AnyDecoder(AbstractSimpleDecoder):
    protoComponent = univ.Any()
    tagFormats = (tag.tagFormatSimple, tag.tagFormatConstructed)
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                     length, state, decodeFun, substrateFun):
        if asn1Spec is None or \
               asn1Spec is not None and tagSet != asn1Spec.getTagSet():
            # untagged Any container, recover inner header substrate
            length = length + len(fullSubstrate) - len(substrate)
            substrate = fullSubstrate
        if substrateFun:
            return substrateFun(self._createComponent(asn1Spec, tagSet),
                                substrate, length)
        head, tail = substrate[:length], substrate[length:]
        return self._createComponent(asn1Spec, tagSet, value=head), tail

    def indefLenValueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet,
                             length, state, decodeFun, substrateFun):
        if asn1Spec is not None and tagSet == asn1Spec.getTagSet():
            # tagged Any type -- consume header substrate
            header = ''
        else:
            # untagged Any, recover header substrate
            header = fullSubstrate[:-len(substrate)]

        r = self._createComponent(asn1Spec, tagSet, header)

        # Any components do not inherit initial tag
        asn1Spec = self.protoComponent
        
        if substrateFun:
            return substrateFun(r, substrate, length)
        while substrate:
            component, substrate = decodeFun(substrate, asn1Spec)
            if eoo.endOfOctets.isSameTypeWith(component) and \
                    component == eoo.endOfOctets:
                break
            r = r + component
        else:
            raise error.SubstrateUnderrunError(
                'No EOO seen before substrate ends'
                )
        return r, substrate

# character string types
class UTF8StringDecoder(OctetStringDecoder):
    protoComponent = char.UTF8String()
class NumericStringDecoder(OctetStringDecoder):
    protoComponent = char.NumericString()
class PrintableStringDecoder(OctetStringDecoder):
    protoComponent = char.PrintableString()
class TeletexStringDecoder(OctetStringDecoder):
    protoComponent = char.TeletexString()
class VideotexStringDecoder(OctetStringDecoder):
    protoComponent = char.VideotexString()
class IA5StringDecoder(OctetStringDecoder):
    protoComponent = char.IA5String()
class GraphicStringDecoder(OctetStringDecoder):
    protoComponent = char.GraphicString()
class VisibleStringDecoder(OctetStringDecoder):
    protoComponent = char.VisibleString()
class GeneralStringDecoder(OctetStringDecoder):
    protoComponent = char.GeneralString()
class UniversalStringDecoder(OctetStringDecoder):
    protoComponent = char.UniversalString()
class BMPStringDecoder(OctetStringDecoder):
    protoComponent = char.BMPString()

# "useful" types
class GeneralizedTimeDecoder(OctetStringDecoder):
    protoComponent = useful.GeneralizedTime()
class UTCTimeDecoder(OctetStringDecoder):
    protoComponent = useful.UTCTime()

tagMap = {
    eoo.endOfOctets.tagSet: EndOfOctetsDecoder(),
    univ.Integer.tagSet: IntegerDecoder(),
    univ.Boolean.tagSet: BooleanDecoder(),
    univ.BitString.tagSet: BitStringDecoder(),
    univ.OctetString.tagSet: OctetStringDecoder(),
    univ.Null.tagSet: NullDecoder(),
    univ.ObjectIdentifier.tagSet: ObjectIdentifierDecoder(),
    univ.Enumerated.tagSet: IntegerDecoder(),
    univ.Real.tagSet: RealDecoder(),
    univ.Sequence.tagSet: SequenceDecoder(),  # conflicts with SequenceOf
    univ.Set.tagSet: SetDecoder(),            # conflicts with SetOf
    univ.Choice.tagSet: ChoiceDecoder(),      # conflicts with Any
    # character string types
    char.UTF8String.tagSet: UTF8StringDecoder(),
    char.NumericString.tagSet: NumericStringDecoder(),
    char.PrintableString.tagSet: PrintableStringDecoder(),
    char.TeletexString.tagSet: TeletexStringDecoder(),
    char.VideotexString.tagSet: VideotexStringDecoder(),
    char.IA5String.tagSet: IA5StringDecoder(),
    char.GraphicString.tagSet: GraphicStringDecoder(),
    char.VisibleString.tagSet: VisibleStringDecoder(),
    char.GeneralString.tagSet: GeneralStringDecoder(),
    char.UniversalString.tagSet: UniversalStringDecoder(),
    char.BMPString.tagSet: BMPStringDecoder(),
    # useful types
    useful.GeneralizedTime.tagSet: GeneralizedTimeDecoder(),
    useful.UTCTime.tagSet: UTCTimeDecoder()
    }

# Type-to-codec map for ambiguous ASN.1 types
typeMap = {
    univ.Set.typeId: SetDecoder(),
    univ.SetOf.typeId: SetOfDecoder(),
    univ.Sequence.typeId: SequenceDecoder(),
    univ.SequenceOf.typeId: SequenceOfDecoder(),
    univ.Choice.typeId: ChoiceDecoder(),
    univ.Any.typeId: AnyDecoder()
    }

( stDecodeTag, stDecodeLength, stGetValueDecoder, stGetValueDecoderByAsn1Spec,
  stGetValueDecoderByTag, stTryAsExplicitTag, stDecodeValue,
  stDumpRawValue, stErrorCondition, stStop ) = [x for x in range(10)]

class Decoder:
    defaultErrorState = stErrorCondition
#    defaultErrorState = stDumpRawValue
    defaultRawDecoder = AnyDecoder()
    def __init__(self, tagMap, typeMap={}):
        self.__tagMap = tagMap
        self.__typeMap = typeMap
        self.__endOfOctetsTagSet = eoo.endOfOctets.getTagSet()
        # Tag & TagSet objects caches
        self.__tagCache = {}
        self.__tagSetCache = {}
        
    def __call__(self, substrate, asn1Spec=None, tagSet=None,
                 length=None, state=stDecodeTag, recursiveFlag=1,
                 substrateFun=None):
        if debug.logger & debug.flagDecoder:
            debug.logger('decoder called at scope %s with state %d, working with up to %d octets of substrate: %s' % (debug.scope, state, len(substrate), debug.hexdump(substrate)))
        fullSubstrate = substrate
        while state != stStop:
            if state == stDecodeTag:
                # Decode tag
                if not substrate:
                    raise error.SubstrateUnderrunError(
                        'Short octet stream on tag decoding'
                        )
                if not isOctetsType(substrate) and \
                   not isinstance(substrate, univ.OctetString):
                    raise error.PyAsn1Error('Bad octet stream type')
                
                firstOctet = substrate[0]
                substrate = substrate[1:]
                if firstOctet in self.__tagCache:
                    lastTag = self.__tagCache[firstOctet]
                else:
                    t = oct2int(firstOctet)
                    tagClass = t&0xC0
                    tagFormat = t&0x20
                    tagId = t&0x1F
                    if tagId == 0x1F:
                        tagId = 0
                        while 1:
                            if not substrate:
                                raise error.SubstrateUnderrunError(
                                    'Short octet stream on long tag decoding'
                                    )
                            t = oct2int(substrate[0])
                            tagId = tagId << 7 | (t&0x7F)
                            substrate = substrate[1:]
                            if not t&0x80:
                                break
                    lastTag = tag.Tag(
                        tagClass=tagClass, tagFormat=tagFormat, tagId=tagId
                        )
                    if tagId < 31:
                        # cache short tags
                        self.__tagCache[firstOctet] = lastTag
                if tagSet is None:
                    if firstOctet in self.__tagSetCache:
                        tagSet = self.__tagSetCache[firstOctet]
                    else:
                        # base tag not recovered
                        tagSet = tag.TagSet((), lastTag)
                        if firstOctet in self.__tagCache:
                            self.__tagSetCache[firstOctet] = tagSet
                else:
                    tagSet = lastTag + tagSet
                state = stDecodeLength
                debug.logger and debug.logger & debug.flagDecoder and debug.logger('tag decoded into %r, decoding length' % tagSet)
            if state == stDecodeLength:
                # Decode length
                if not substrate:
                     raise error.SubstrateUnderrunError(
                         'Short octet stream on length decoding'
                         )
                firstOctet  = oct2int(substrate[0])
                if firstOctet == 128:
                    size = 1
                    length = -1
                elif firstOctet < 128:
                    length, size = firstOctet, 1
                else:
                    size = firstOctet & 0x7F
                    # encoded in size bytes
                    length = 0
                    lengthString = substrate[1:size+1]
                    # missing check on maximum size, which shouldn't be a
                    # problem, we can handle more than is possible
                    if len(lengthString) != size:
                        raise error.SubstrateUnderrunError(
                            '%s<%s at %s' %
                            (size, len(lengthString), tagSet)
                            )
                    for char in lengthString:
                        length = (length << 8) | oct2int(char)
                    size = size + 1
                substrate = substrate[size:]
                if length != -1 and len(substrate) < length:
                    raise error.SubstrateUnderrunError(
                        '%d-octet short' % (length - len(substrate))
                        )
                state = stGetValueDecoder
                debug.logger and debug.logger & debug.flagDecoder and debug.logger('value length decoded into %d, payload substrate is: %s' % (length, debug.hexdump(length == -1 and substrate or substrate[:length])))
            if state == stGetValueDecoder:
                if asn1Spec is None:
                    state = stGetValueDecoderByTag
                else:
                    state = stGetValueDecoderByAsn1Spec
            #
            # There're two ways of creating subtypes in ASN.1 what influences
            # decoder operation. These methods are:
            # 1) Either base types used in or no IMPLICIT tagging has been
            #    applied on subtyping.
            # 2) Subtype syntax drops base type information (by means of
            #    IMPLICIT tagging.
            # The first case allows for complete tag recovery from substrate
            # while the second one requires original ASN.1 type spec for
            # decoding.
            #
            # In either case a set of tags (tagSet) is coming from substrate
            # in an incremental, tag-by-tag fashion (this is the case of
            # EXPLICIT tag which is most basic). Outermost tag comes first
            # from the wire.
            #            
            if state == stGetValueDecoderByTag:
                if tagSet in self.__tagMap:
                    concreteDecoder = self.__tagMap[tagSet]
                else:
                    concreteDecoder = None
                if concreteDecoder:
                    state = stDecodeValue
                else:
                    _k = tagSet[:1]
                    if _k in self.__tagMap:
                        concreteDecoder = self.__tagMap[_k]
                    else:
                        concreteDecoder = None
                    if concreteDecoder:
                        state = stDecodeValue
                    else:
                        state = stTryAsExplicitTag
                if debug.logger and debug.logger & debug.flagDecoder:
                    debug.logger('codec %s chosen by a built-in type, decoding %s' % (concreteDecoder and concreteDecoder.__class__.__name__ or "<none>", state == stDecodeValue and 'value' or 'as explicit tag'))
                    debug.scope.push(concreteDecoder is None and '?' or concreteDecoder.protoComponent.__class__.__name__)
            if state == stGetValueDecoderByAsn1Spec:
                if isinstance(asn1Spec, (dict, tagmap.TagMap)):
                    if tagSet in asn1Spec:
                        __chosenSpec = asn1Spec[tagSet]
                    else:
                        __chosenSpec = None
                    if debug.logger and debug.logger & debug.flagDecoder:
                        debug.logger('candidate ASN.1 spec is a map of:')
                        for t, v in asn1Spec.getPosMap().items():
                            debug.logger('  %r -> %s' % (t, v.__class__.__name__))
                        if asn1Spec.getNegMap():
                            debug.logger('but neither of: ')
                            for i in asn1Spec.getNegMap().items():
                                debug.logger('  %r -> %s' % (t, v.__class__.__name__))
                        debug.logger('new candidate ASN.1 spec is %s, chosen by %r' % (__chosenSpec is None and '<none>' or __chosenSpec.__class__.__name__, tagSet))
                else:
                    __chosenSpec = asn1Spec
                    debug.logger and debug.logger & debug.flagDecoder and debug.logger('candidate ASN.1 spec is %s' % asn1Spec.__class__.__name__)
                if __chosenSpec is not None and (
                       tagSet == __chosenSpec.getTagSet() or \
                       tagSet in __chosenSpec.getTagMap()
                       ):
                    # use base type for codec lookup to recover untagged types
                    baseTagSet = __chosenSpec.baseTagSet
                    if __chosenSpec.typeId is not None and \
                           __chosenSpec.typeId in self.__typeMap:
                        # ambiguous type
                        concreteDecoder = self.__typeMap[__chosenSpec.typeId]
                        debug.logger and debug.logger & debug.flagDecoder and debug.logger('value decoder chosen for an ambiguous type by type ID %s' % (__chosenSpec.typeId,))
                    elif baseTagSet in self.__tagMap:
                        # base type or tagged subtype
                        concreteDecoder = self.__tagMap[baseTagSet]
                        debug.logger and debug.logger & debug.flagDecoder and debug.logger('value decoder chosen by base %r' % (baseTagSet,))
                    else:
                        concreteDecoder = None
                    if concreteDecoder:
                        asn1Spec = __chosenSpec
                        state = stDecodeValue
                    else:
                        state = stTryAsExplicitTag
                elif tagSet == self.__endOfOctetsTagSet:
                    concreteDecoder = self.__tagMap[tagSet]
                    state = stDecodeValue
                    debug.logger and debug.logger & debug.flagDecoder and debug.logger('end-of-octets found')
                else:
                    concreteDecoder = None
                    state = stTryAsExplicitTag
                if debug.logger and debug.logger & debug.flagDecoder:
                    debug.logger('codec %s chosen by ASN.1 spec, decoding %s' % (state == stDecodeValue and concreteDecoder.__class__.__name__ or "<none>", state == stDecodeValue and 'value' or 'as explicit tag'))
                    debug.scope.push(__chosenSpec is None and '?' or __chosenSpec.__class__.__name__)
            if state == stTryAsExplicitTag:
                if tagSet and \
                       tagSet[0][1] == tag.tagFormatConstructed and \
                       tagSet[0][0] != tag.tagClassUniversal:
                    # Assume explicit tagging
                    concreteDecoder = explicitTagDecoder
                    state = stDecodeValue
                else:                    
                    concreteDecoder = None
                    state = self.defaultErrorState
                debug.logger and debug.logger & debug.flagDecoder and debug.logger('codec %s chosen, decoding %s' % (concreteDecoder and concreteDecoder.__class__.__name__ or "<none>", state == stDecodeValue and 'value' or 'as failure'))
            if state == stDumpRawValue:
                concreteDecoder = self.defaultRawDecoder
                debug.logger and debug.logger & debug.flagDecoder and debug.logger('codec %s chosen, decoding value' % concreteDecoder.__class__.__name__)
                state = stDecodeValue
            if state == stDecodeValue:
                if recursiveFlag == 0 and not substrateFun: # legacy
                    substrateFun = lambda a,b,c: (a,b[:c])
                if length == -1:  # indef length
                    value, substrate = concreteDecoder.indefLenValueDecoder(
                        fullSubstrate, substrate, asn1Spec, tagSet, length,
                        stGetValueDecoder, self, substrateFun
                        )
                else:
                    value, substrate = concreteDecoder.valueDecoder(
                        fullSubstrate, substrate, asn1Spec, tagSet, length,
                        stGetValueDecoder, self, substrateFun
                        )
                state = stStop
                debug.logger and debug.logger & debug.flagDecoder and debug.logger('codec %s yields type %s, value:\n%s\n...remaining substrate is: %s' % (concreteDecoder.__class__.__name__, value.__class__.__name__, value.prettyPrint(), substrate and debug.hexdump(substrate) or '<none>'))
            if state == stErrorCondition:
                raise error.PyAsn1Error(
                    '%r not in asn1Spec: %r' % (tagSet, asn1Spec)
                    )
        if debug.logger and debug.logger & debug.flagDecoder:
            debug.scope.pop()
            debug.logger('decoder left scope %s, call completed' % debug.scope)
        return value, substrate
            
decode = Decoder(tagMap, typeMap)

# XXX
# non-recursive decoding; return position rather than substrate
