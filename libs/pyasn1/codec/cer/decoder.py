# CER decoder
from libs.pyasn1 import error
from libs.pyasn1.codec.ber import decoder
from libs.pyasn1.compat.octets import oct2int
from libs.pyasn1.type import univ


class BooleanDecoder(decoder.AbstractSimpleDecoder):
    protoComponent = univ.Boolean(0)
    def valueDecoder(self, fullSubstrate, substrate, asn1Spec, tagSet, length,
                     state, decodeFun, substrateFun):
        head, tail = substrate[:length], substrate[length:]
        if not head:
            raise error.PyAsn1Error('Empty substrate')
        byte = oct2int(head[0])
        # CER/DER specifies encoding of TRUE as 0xFF and FALSE as 0x0, while
        # BER allows any non-zero value as TRUE; cf. sections 8.2.2. and 11.1 
        # in http://www.itu.int/ITU-T/studygroups/com17/languages/X.690-0207.pdf
        if byte == 0xff:
            value = 1
        elif byte == 0x00:
            value = 0
        else:
            raise error.PyAsn1Error('Boolean CER violation: %s' % byte)
        return self._createComponent(asn1Spec, tagSet, value), tail

tagMap = decoder.tagMap.copy()
tagMap.update({
    univ.Boolean.tagSet: BooleanDecoder()
    })

typeMap = decoder.typeMap

class Decoder(decoder.Decoder): pass

decode = Decoder(tagMap, decoder.typeMap)
