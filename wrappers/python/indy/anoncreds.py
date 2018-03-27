from .libindy import do_call, create_cb

from typing import Optional
from ctypes import *

import logging


async def issuer_create_schema(issuer_did: str,
                               name: str,
                               version: str,
                               attrs: str) -> (str, str):
    """
    Create credential schema entity that describes credential attributes list and allows credentials
    interoperability.

    Schema is public and intended to be shared with all anoncreds workflow actors usually by publishing SCHEMA transaction
    to Indy distributed ledger.

    :param issuer_did: DID of schema issuer
    :param name: a name the schema
    :param version: a version of the schema
    :param attrs: a list of schema attributes descriptions
    :return:
        schema_id: identifier of created schema
        schema_json: schema as json
    """

    logger = logging.getLogger(__name__)
    logger.debug("issuer_create_schema: >>> issuer_did: %r, name: %r, version: %r, attrs: %r",
                 issuer_did,
                 name,
                 version,
                 attrs)

    if not hasattr(issuer_create_schema, "cb"):
        logger.debug("issuer_create_schema: Creating callback")
        issuer_create_schema.cb = create_cb(CFUNCTYPE(None, c_int32, c_int32, c_char_p, c_char_p))

    c_issuer_did = c_char_p(issuer_did.encode('utf-8'))
    c_name = c_char_p(name.encode('utf-8'))
    c_version = c_char_p(version.encode('utf-8'))
    c_attrs = c_char_p(attrs.encode('utf-8'))

    (schema_id, schema_json) = await do_call('indy_issuer_create_schema',
                                             c_issuer_did,
                                             c_name,
                                             c_version,
                                             c_attrs,
                                             issuer_create_schema.cb)

    res = (schema_id.decode(), schema_json.decode())
    logger.debug("issuer_create_schema: <<< res: %r", res)
    return res


async def issuer_create_and_store_credential_def(wallet_handle: int,
                                                 issuer_did: str,
                                                 schema_json: str,
                                                 tag: str,
                                                 type_: Optional[str],
                                                 config_json: str) -> (str, str):
    """
    Create credential definition entity that encapsulates credentials issuer DID, credential schema, secrets used for
    signing credentials and secrets used for credentials revocation.

    Credential definition entity contains private and public parts. Private part will be stored in the wallet.
    Public part will be returned as json intended to be shared with all anoncreds workflow actors usually by
    publishing CRED_DEF transaction to Indy distributed ledger.

    :param wallet_handle: wallet handler (created by open_wallet).
    :param issuer_did: a DID of the issuer signing cred_def transaction to the Ledger
    :param schema_json: credential schema as a json
    :param tag: allows to distinct between credential definitions for the same issuer and schema
    :param type_: credential definition type (optional, 'CL' by default) that defines claims signature and revocation math.
    Supported types are:
        - 'CL': Camenisch-Lysyanskaya credential signature type
    :param  config_json: type-specific configuration of credential definition as json:
        - 'CL':
          - support_revocation: whether to request non-revocation credential (optional, default false)
    :return: 
        cred_def_id: identifier of created credential definition
        cred_def_json: public part of created credential definition
    """

    logger = logging.getLogger(__name__)
    logger.debug("issuer_create_and_store_credential_def: >>> wallet_handle: %r, issuer_did: %r, schema_json: %r,"
                 " tag: %r, type_: %r, config_json: %r",
                 wallet_handle,
                 issuer_did,
                 schema_json,
                 tag,
                 type_,
                 config_json)

    if not hasattr(issuer_create_and_store_credential_def, "cb"):
        logger.debug("issuer_create_and_store_credential_def: Creating callback")
        issuer_create_and_store_credential_def.cb = create_cb(CFUNCTYPE(None, c_int32, c_int32, c_char_p, c_char_p))

    c_wallet_handle = c_int32(wallet_handle)
    c_issuer_did = c_char_p(issuer_did.encode('utf-8'))
    c_schema_json = c_char_p(schema_json.encode('utf-8'))
    c_tag = c_char_p(tag.encode('utf-8'))
    c_type = c_char_p(type_.encode('utf-8')) if type_ is not None else None
    c_config_json = c_char_p(config_json.encode('utf-8'))

    (credential_def_id, credential_def_json) = await do_call('indy_issuer_create_and_store_credential_def',
                                                             c_wallet_handle,
                                                             c_issuer_did,
                                                             c_schema_json,
                                                             c_tag,
                                                             c_type,
                                                             c_config_json,
                                                             issuer_create_and_store_credential_def.cb)

    res = (credential_def_id.decode(), credential_def_json.decode())
    logger.debug("issuer_create_and_store_credential_def: <<< res: %r", res)
    return res


async def issuer_create_and_store_revoc_reg(wallet_handle: int,
                                            issuer_did: str,
                                            type_: Optional[str],
                                            tag: str,
                                            cred_def_id: str,
                                            config_json: str,
                                            tails_writer_handle: int) -> (str, str, str):
    """
    Create a new revocation registry for the given credential definition as tuple of entities:
    - Revocation registry definition that encapsulates credentials definition reference, revocation type specific configuration and
      secrets used for credentials revocation
    - Revocation registry state that stores the information about revoked entities in a non-disclosing way. The state can be
      represented as ordered list of revocation registry entries were each entry represents the list of revocation or issuance operations.

    Revocation registry definition entity contains private and public parts. Private part will be stored in the wallet. Public part
    will be returned as json intended to be shared with all anoncreds workflow actors usually by publishing REVOC_REG_DEF transaction
    to Indy distributed ledger.

    Revocation registry state is stored on the wallet and also intended to be shared as the ordered list of REVOC_REG_ENTRY transactions.
    This call initializes the state in the wallet and returns the initial entry.

    Some revocation registry types (for example, 'CL_ACCUM') can require generation of binary blob called tails used to hide information about revoked claims in public
    revocation registry and intended to be distributed out of leger (REVOC_REG_DEF transaction will still contain uri and hash of tails).
    This call requires access to pre-configured blob storage writer instance handle that will allow to write generated tails.

    :param wallet_handle: wallet handler (created by open_wallet).
    :param issuer_did: a DID of the issuer signing transaction to the Ledger
    :param type_: type_: revocation registry type (optional, default value depends on claim definition type). Supported types are:
        - 'CL_ACCUM': Type-3 pairing based accumulator. Default for 'CL' claim definition type
    :param tag: allows to distinct between revocation registries for the same issuer and credential definition
    :param cred_def_id: id of stored in ledger credential definition
    :param config_json: type-specific configuration of revocation registry as json:
        - 'CL_ACCUM':
            "issuance_type": (optional) type of issuance. Currently supported:
                1) ISSUANCE_BY_DEFAULT: all indices are assumed to be issued and initial accumulator is calculated over all indices;
                   Revocation Registry is updated only during revocation.
                2) ISSUANCE_ON_DEMAND: nothing is issued initially accumulator is 1 (used by default);
            "max_cred_num": maximum number of claims the new registry can process (optional, default 100000)
        }
    :param tails_writer_handle:
    :return: 
        revoc_reg_id: identifier of created revocation registry definition
        revoc_reg_def_json: public part of revocation registry definition
        revoc_reg_entry_json: revocation registry entry that defines initial state of revocation registry
    """

    logger = logging.getLogger(__name__)
    logger.debug("issuer_create_and_store_revoc_reg: >>> wallet_handle: %r, issuer_did: %r, type_: %r,"
                 " tag: %r, cred_def_id: %r, config_json: %r, tails_writer_handle: %r",
                 wallet_handle,
                 issuer_did,
                 type_,
                 tag,
                 cred_def_id,
                 config_json,
                 tails_writer_handle)

    if not hasattr(issuer_create_and_store_revoc_reg, "cb"):
        logger.debug("issuer_create_and_store_revoc_reg: Creating callback")
        issuer_create_and_store_revoc_reg.cb = create_cb(
            CFUNCTYPE(None, c_int32, c_int32, c_char_p, c_char_p, c_char_p))

    c_wallet_handle = c_int32(wallet_handle)
    c_issuer_did = c_char_p(issuer_did.encode('utf-8'))
    c_type = c_char_p(type_.encode('utf-8')) if type_ is not None else None
    c_tag = c_char_p(tag.encode('utf-8'))
    c_cred_def_id = c_char_p(cred_def_id.encode('utf-8'))
    c_config_json = c_char_p(config_json.encode('utf-8'))
    c_tails_writer_handle = c_int32(tails_writer_handle)

    (rev_reg_id, rev_reg_def_json, rev_reg_entry_json) = await do_call('indy_issuer_create_and_store_revoc_reg',
                                                                       c_wallet_handle,
                                                                       c_issuer_did,
                                                                       c_type,
                                                                       c_tag,
                                                                       c_cred_def_id,
                                                                       c_config_json,
                                                                       c_tails_writer_handle,
                                                                       issuer_create_and_store_revoc_reg.cb)
    res = (rev_reg_id.decode(), rev_reg_def_json.decode(), rev_reg_entry_json.decode())
    logger.debug("issuer_create_and_store_revoc_reg: <<< res: %r", res)
    return res


async def issuer_create_credential_offer(wallet_handle: int,
                                         cred_def_id: str) -> str:
    """
    Create credential offer that will be used by Prover for
    claim request creation. Offer includes nonce and key correctness proof
    for authentication between protocol steps and integrity checking.

    :param wallet_handle: wallet handler (created by open_wallet).
    :param cred_def_id: id of credential definition stored in the wallet
    :return:
    credential offer json:
         {
             "cred_def_id": string,
             # Fields below can depend on Cred Def type
             "nonce": string,
             "key_correctness_proof" : <key_correctness_proof>
         }
    """

    logger = logging.getLogger(__name__)
    logger.debug("issuer_create_credential_offer: >>> wallet_handle: %r, cred_def_id: %r",
                 wallet_handle,
                 cred_def_id)

    if not hasattr(issuer_create_credential_offer, "cb"):
        logger.debug("issuer_create_credential_offer: Creating callback")
        issuer_create_credential_offer.cb = create_cb(CFUNCTYPE(None, c_int32, c_int32, c_char_p))

    c_wallet_handle = c_int32(wallet_handle)
    c_cred_def_id = c_char_p(cred_def_id.encode('utf-8'))

    credential_offer_json = await do_call('indy_issuer_create_credential_offer',
                                          c_wallet_handle,
                                          c_cred_def_id,
                                          issuer_create_credential_offer.cb)

    res = credential_offer_json.decode()
    logger.debug("issuer_create_credential_offer: <<< res: %r", res)
    return res


async def issuer_create_credential(wallet_handle: int,
                                   cred_offer_json: str,
                                   cred_req_json: str,
                                   cred_values_json: str,
                                   rev_reg_id: Optional[str],
                                   blob_storage_reader_handle: Optional[int]) -> (str, Optional[str], Optional[str]):
    """
    Check Cred Request for the given Cred Offer and issue Credential for the given Cred Request.

    Cred Request must match Cred Offer. The credential definition and revocation registry definition
    referenced in Cred Offer and Cred Request must be already created and stored into the wallet.

    Information for this credential revocation will be store in the wallet as part of revocation registry under
    generated cred_revoc_id local for this wallet.

    This call returns revoc registry delta as json file intended to be shared as REVOC_REG_ENTRY transaction.
    Note that it is possible to accumulate deltas to reduce ledger load.

    :param wallet_handle: wallet handle (created by open_wallet).
    :param cred_offer_json: a cred offer created by issuer_create_credential_offer
    :param cred_req_json: a credential request created by prover_create_credential_req
    :param cred_values_json: a credential containing attribute values for each of requested attribute names.
     Example:
     {
      "attr1" : {"raw": "value1", "encoded": "value1_as_int" },
      "attr2" : {"raw": "value1", "encoded": "value1_as_int" }
     }
    :param rev_reg_id: (Optional) id of revocation registry definition stored in the wallet
    :param blob_storage_reader_handle: pre-configured blob storage reader instance handle that
    will allow to read revocation tails
    :return: 
     cred_json: Credential json containing signed credential values
         {
             "cred_def_id": string,
             "rev_reg_def_id", Optional<string>,
             "values": <see credential_values_json above>,
             // Fields below can depend on Cred Def type
             "signature": <signature>,
             "signature_correctness_proof": <signature_correctness_proof>
         }
     cred_revoc_id: local id for revocation info (Can be used for revocation of this cred)
     revoc_reg_delta_json: Revocation registry delta json with a newly issued credential
    """

    logger = logging.getLogger(__name__)
    logger.debug("issuer_create_credential: >>> wallet_handle: %r, cred_offer_json: %r, cred_req_json: %r,"
                 " cred_values_json: %r, rev_reg_id: %r, blob_storage_reader_handle: %r",
                 wallet_handle,
                 cred_offer_json,
                 cred_req_json,
                 cred_values_json,
                 rev_reg_id,
                 blob_storage_reader_handle)

    if not hasattr(issuer_create_credential, "cb"):
        logger.debug("issuer_create_credential: Creating callback")
        issuer_create_credential.cb = create_cb(CFUNCTYPE(None, c_int32, c_int32, c_char_p, c_char_p, c_char_p))

    c_wallet_handle = c_int32(wallet_handle)
    c_cred_offer_json = c_char_p(cred_offer_json.encode('utf-8'))
    c_cred_req_json = c_char_p(cred_req_json.encode('utf-8'))
    c_cred_values_json = c_char_p(cred_values_json.encode('utf-8'))
    c_rev_reg_id = c_char_p(rev_reg_id.encode('utf-8')) if rev_reg_id is not None else None
    c_blob_storage_reader_handle = c_int32(blob_storage_reader_handle) if blob_storage_reader_handle else -1

    (cred_json, cred_revoc_id, revoc_reg_delta_json) = await do_call('indy_issuer_create_credential',
                                                                     c_wallet_handle,
                                                                     c_cred_offer_json,
                                                                     c_cred_req_json,
                                                                     c_cred_values_json,
                                                                     c_rev_reg_id,
                                                                     c_blob_storage_reader_handle,
                                                                     issuer_create_credential.cb)
    cred_json = cred_json.decode()
    cred_revoc_id = cred_revoc_id.decode() if cred_revoc_id else None
    revoc_reg_delta_json = revoc_reg_delta_json.decode() if revoc_reg_delta_json else None
    res = (cred_json, cred_revoc_id, revoc_reg_delta_json)

    logger.debug("issuer_create_credential: <<< res: %r", res)
    return res


async def issuer_revoke_credential(wallet_handle: int,
                                   blob_storage_reader_handle: int,
                                   rev_reg_id: str,
                                   cred_revoc_id: str) -> str:
    """
    Revoke a credential identified by a cred_revoc_id (returned by indy_issuer_create_cred).

    The corresponding credential definition and revocation registry must be already
    created an stored into the wallet.

    This call returns revoc registry delta as json file intended to be shared as REVOC_REG_ENTRY transaction.
    Note that it is possible to accumulate deltas to reduce ledger load.

    :param wallet_handle: wallet handler (created by open_wallet).
    :param blob_storage_reader_handle: pre-configured blob storage reader instance handle that will allow
    to read revocation tails
    :param rev_reg_id: id of revocation registry stored in wallet
    :param cred_revoc_id: local id for revocation info
    :return: Revocation registry update json with a revoked credential
    """

    logger = logging.getLogger(__name__)
    logger.debug(
        "issuer_revoke_credential: >>> wallet_handle: %r, blob_storage_reader_handle: %r, rev_reg_id: %r, "
        "cred_revoc_id: %r",
        wallet_handle,
        blob_storage_reader_handle,
        rev_reg_id,
        cred_revoc_id)

    if not hasattr(issuer_revoke_credential, "cb"):
        logger.debug("issuer_revoke_credential: Creating callback")
        issuer_revoke_credential.cb = create_cb(CFUNCTYPE(None, c_int32, c_int32, c_char_p))

    c_wallet_handle = c_int32(wallet_handle)
    c_blob_storage_reader_handle = c_int32(blob_storage_reader_handle)
    c_rev_reg_id = c_char_p(rev_reg_id.encode('utf-8'))
    c_cred_revoc_id = c_char_p(cred_revoc_id.encode('utf-8'))

    revoc_reg_delta_json = await do_call('indy_issuer_revoke_credential',
                                         c_wallet_handle,
                                         c_blob_storage_reader_handle,
                                         c_rev_reg_id,
                                         c_cred_revoc_id,
                                         issuer_revoke_credential.cb)
    res = revoc_reg_delta_json.decode()
    logger.debug("issuer_revoke_credential: <<< res: %r", res)
    return res


async def issuer_recover_credential(wallet_handle: int,
                                    blob_storage_reader_handle: int,
                                    rev_reg_id: str,
                                    cred_revoc_id: str) -> str:
    """
    Recover a credential identified by a cred_revoc_id (returned by indy_issuer_create_cred).

    The corresponding credential definition and revocation registry must be already
    created an stored into the wallet.

    This call returns revoc registry delta as json file intended to be shared as REVOC_REG_ENTRY transaction.
    Note that it is possible to accumulate deltas to reduce ledger load.

    :param wallet_handle: wallet handler (created by open_wallet).
    :param blob_storage_reader_handle: pre-configured blob storage reader instance handle that will allow
    to read revocation tails
    :param rev_reg_id: id of revocation registry stored in wallet
    :param cred_revoc_id: local id for revocation info
    :return: Revocation registry update json with a revoked credential
    """

    logger = logging.getLogger(__name__)
    logger.debug(
        "issuer_recover_credential: >>> wallet_handle: %r, blob_storage_reader_handle: %r, rev_reg_id: %r, "
        "cred_revoc_id: %r",
        wallet_handle,
        blob_storage_reader_handle,
        rev_reg_id,
        cred_revoc_id)

    if not hasattr(issuer_recover_credential, "cb"):
        logger.debug("issuer_recover_credential: Creating callback")
        issuer_recover_credential.cb = create_cb(CFUNCTYPE(None, c_int32, c_int32, c_char_p))

    c_wallet_handle = c_int32(wallet_handle)
    c_blob_storage_reader_handle = c_int32(blob_storage_reader_handle)
    c_rev_reg_id = c_char_p(rev_reg_id.encode('utf-8'))
    c_cred_revoc_id = c_char_p(cred_revoc_id.encode('utf-8'))

    revoc_reg_delta_json = await do_call('indy_issuer_recover_credential',
                                         c_wallet_handle,
                                         c_blob_storage_reader_handle,
                                         c_rev_reg_id,
                                         c_cred_revoc_id,
                                         issuer_recover_credential.cb)
    res = revoc_reg_delta_json.decode()
    logger.debug("issuer_recover_credential: <<< res: %r", res)
    return res


async def issuer_merge_revocation_registry_deltas(rev_reg_delta_json: str,
                                                  other_rev_reg_delta_json: str) -> str:
    logger = logging.getLogger(__name__)
    logger.debug(
        "issuer_merge_revocation_registry_deltas: >>> rev_reg_delta_json: %r, other_rev_reg_delta_json: %r",
        rev_reg_delta_json,
        other_rev_reg_delta_json)

    if not hasattr(issuer_merge_revocation_registry_deltas, "cb"):
        logger.debug("issuer_merge_revocation_registry_deltas: Creating callback")
        issuer_merge_revocation_registry_deltas.cb = create_cb(CFUNCTYPE(None, c_int32, c_int32, c_char_p))

    c_rev_reg_delta_json = c_char_p(rev_reg_delta_json.encode('utf-8'))
    c_other_rev_reg_delta_json = c_char_p(other_rev_reg_delta_json.encode('utf-8'))

    merged_revoc_reg_delta_json = await do_call('indy_issuer_merge_revocation_registry_deltas',
                                                c_rev_reg_delta_json,
                                                c_other_rev_reg_delta_json,
                                                issuer_merge_revocation_registry_deltas.cb)
    res = merged_revoc_reg_delta_json.decode()
    logger.debug("issuer_merge_revocation_registry_deltas: <<< res: %r", res)
    return res


async def prover_create_master_secret(wallet_handle: int,
                                      master_secret_name: str) -> str:
    """
    Creates a master secret with a given name and stores it in the wallet.
    The name must be unique.

    :param wallet_handle: wallet handler (created by open_wallet).
    :param master_secret_name: a new master secret name
    :return: None.
    """

    logger = logging.getLogger(__name__)
    logger.debug("prover_create_master_secret: >>> wallet_handle: %r, master_secret_name: %r",
                 wallet_handle,
                 master_secret_name)

    if not hasattr(prover_create_master_secret, "cb"):
        logger.debug("prover_create_master_secret: Creating callback")
        prover_create_master_secret.cb = create_cb(CFUNCTYPE(None, c_int32, c_int32, c_char_p))

    c_wallet_handle = c_int32(wallet_handle)
    c_master_secret_name = c_char_p(master_secret_name.encode('utf-8'))

    out_master_secret_id = await do_call('indy_prover_create_master_secret',
                                         c_wallet_handle,
                                         c_master_secret_name,
                                         prover_create_master_secret.cb)

    res = out_master_secret_id.decode()
    logger.debug("prover_create_master_secret: <<< res: %r", res)
    return res


async def prover_create_credential_req(wallet_handle: int,
                                       prover_did: str,
                                       cred_offer_json: str,
                                       cred_def_json: str,
                                       master_secret_id: str) -> (str, str):
    """
    Creates a clam request for the given credential offer.

    The method creates a blinded master secret for a master secret identified by a provided name.
    The master secret identified by the name must be already stored in the secure wallet (see prover_create_master_secret)
    The blinded master secret is a part of the credential request.

    :param wallet_handle: wallet handler (created by open_wallet).
    :param prover_did: a DID of the prover
    :param cred_offer_json: a cred offer created by issuer_create_credential_offer
    :param cred_def_json: credential definition json created by indy_issuer_create_and_store_credential_def
    :param master_secret_id: the id of the master secret stored in the wallet
    :return: 
     cred_req_json: Credential request json for creation of credential by Issuer
         {
          "cred_def_id" : string,
          "rev_reg_id" : Optional<string>,
          "prover_did" : string,
             // Fields below can depend on Cred Def type
          "blinded_ms" : <blinded_master_secret>,
          "blinded_ms_correctness_proof" : <blinded_ms_correctness_proof>,
          "nonce": string
        }
     cred_req_metadata_json: Credential request metadata json for processing of received form Issuer credential.
    """

    logger = logging.getLogger(__name__)
    logger.debug("prover_create_credential_req: >>> wallet_handle: %r, prover_did: %r, cred_offer_json: %r,"
                 " cred_def_json: %r, master_secret_id: %r",
                 wallet_handle,
                 prover_did,
                 cred_offer_json,
                 cred_def_json,
                 master_secret_id)

    if not hasattr(prover_create_credential_req, "cb"):
        logger.debug("prover_create_credential_req: Creating callback")
        prover_create_credential_req.cb = create_cb(CFUNCTYPE(None, c_int32, c_int32, c_char_p, c_char_p))

    c_wallet_handle = c_int32(wallet_handle)
    c_prover_did = c_char_p(prover_did.encode('utf-8'))
    c_cred_offer_json = c_char_p(cred_offer_json.encode('utf-8'))
    c_cred_def_json = c_char_p(cred_def_json.encode('utf-8'))
    c_master_secret_id = c_char_p(master_secret_id.encode('utf-8'))

    (credential_req_json, credential_req_metadata_json) = await do_call('indy_prover_create_credential_req',
                                                                        c_wallet_handle,
                                                                        c_prover_did,
                                                                        c_cred_offer_json,
                                                                        c_cred_def_json,
                                                                        c_master_secret_id,
                                                                        prover_create_credential_req.cb)

    credential_req_json = credential_req_json.decode()
    credential_req_metadata_json = credential_req_metadata_json.decode()
    res = (credential_req_json, credential_req_metadata_json)

    logger.debug("prover_create_credential_req: <<< res: %r", res)
    return res


async def prover_store_credential(wallet_handle: int,
                                  cred_id: str,
                                  cred_req_json: str,
                                  cred_req_metadata_json: str,
                                  cred_json: str,
                                  cred_def_json: str,
                                  rev_reg_def_json: Optional[str]) -> str:
    """
    Check credential provided by Issuer for the given credential request,
    updates the credential by a master secret and stores in a secure wallet.

    :param wallet_handle: wallet handler (created by open_wallet).
    :param cred_id: (optional, default is a random one) identifier by which credential will be stored in the wallet
    :param cred_req_json: a credential request created by indy_prover_create_cred_request
    :param cred_req_metadata_json: a credential request metadata created by indy_prover_create_cred_request
    :param cred_json: credential json created by indy_issuer_create_cred
    :param cred_def_json: credential definition json created by issuer_create_and_store_credential_def
    :param rev_reg_def_json: revocation registry definition json created by issuer_create_and_store_revoc_reg
    :return: cred_id: identifier by which credential is stored in the wallet
    """

    logger = logging.getLogger(__name__)
    logger.debug("prover_store_credential: >>> wallet_handle: %r, cred_id: %r, cred_req_json: %r, "
                 "cred_req_metadata_json: %r, cred_json: %r, cred_def_json: %r, rev_reg_def_json: %r",
                 wallet_handle,
                 cred_id,
                 cred_req_json,
                 cred_req_metadata_json,
                 cred_json,
                 cred_def_json,
                 rev_reg_def_json)

    if not hasattr(prover_store_credential, "cb"):
        logger.debug("prover_store_credential: Creating callback")
        prover_store_credential.cb = create_cb(CFUNCTYPE(None, c_int32, c_int32, c_char_p))

    c_wallet_handle = c_int32(wallet_handle)
    c_cred_id = c_char_p(cred_id.encode('utf-8'))
    c_cred_req_json = c_char_p(cred_req_json.encode('utf-8'))
    c_cred_req_metadata_json = c_char_p(cred_req_metadata_json.encode('utf-8'))
    c_cred_json = c_char_p(cred_json.encode('utf-8'))
    c_cred_def_json = c_char_p(cred_def_json.encode('utf-8'))
    c_rev_reg_def_json = c_char_p(rev_reg_def_json.encode('utf-8')) if rev_reg_def_json else None

    cred_id = await do_call('indy_prover_store_credential',
                            c_wallet_handle,
                            c_cred_id,
                            c_cred_req_json,
                            c_cred_req_metadata_json,
                            c_cred_json,
                            c_cred_def_json,
                            c_rev_reg_def_json,
                            prover_store_credential.cb)

    res = cred_id.decode()
    logger.debug("prover_store_credential: <<< res: %r", res)
    return res


async def prover_get_credentials(wallet_handle: int,
                                 filter_json: str) -> str:
    """
    Gets human readable credentials according to the filter.
    If filter is NULL, then all credentials are returned.
    credentials can be filtered by Issuer, credential_def and/or Schema.

    :param wallet_handle: wallet handler (created by open_wallet).
    :param filter_json: filter for credentials
        {
            "schema_id": string, (Optional)
            "schema_issuer_did": string, (Optional)
            "schema_name": string, (Optional)
            "schema_version": string, (Optional)
            "issuer_did": string, (Optional)
            "issuer_did": string, (Optional)
            "cred_def_id": string, (Optional)
        }
    :return:  credentials json
     [{
         "referent": string, // cred_id in the wallet
         "values": <see credential_values_json above>,
         "cred_def_id": string,
         "rev_reg_id": Optional<string>,
         "cred_rev_id": Optional<string>
     }]
    """

    logger = logging.getLogger(__name__)
    logger.debug("prover_get_credentials: >>> wallet_handle: %r, filter_json: %r",
                 wallet_handle,
                 filter_json)

    if not hasattr(prover_get_credentials, "cb"):
        logger.debug("prover_get_credentials: Creating callback")
        prover_get_credentials.cb = create_cb(CFUNCTYPE(None, c_int32, c_int32, c_char_p))

    c_wallet_handle = c_int32(wallet_handle)
    c_filter_json = c_char_p(filter_json.encode('utf-8'))

    credentials_json = await do_call('indy_prover_get_credentials',
                                     c_wallet_handle,
                                     c_filter_json,
                                     prover_get_credentials.cb)

    res = credentials_json.decode()
    logger.debug("prover_get_credentials: <<< res: %r", res)
    return res


async def prover_get_credentials_for_proof_req(wallet_handle: int,
                                               proof_request_json: str) -> str:
    """
    Gets human readable credentials matching the given proof request.

    :param wallet_handle: wallet handler (created by open_wallet).
    :param proof_request_json: proof request json
         {
             "name": string,
             "version": string,
             "nonce": string,
             "requested_attrs": { // set of requested attributes
                  "<attr_referent>": <attr_info>, // see below
                  ...,
             },
             "requested_predicates": { // set of requested predicates
                  "<predicate_referent>": <predicate_info>, // see below
                  ...,
              },
             "non_revoked": Optional<<non_revoc_interval>>, // see below,
                            // If specified prover must proof non-revocation
                            // for date in this interval for each attribute
                            // (can be overridden on attribute level)
         }
        where:
         attr_referent: Proof-request local identifier of requested attribute
         attr_info: Describes requested attribute
             {
                 "name": string, // attribute name, (case insensitive and ignore spaces)
                 "restrictions": Optional<[<attr_filter>]> // see below,
        //                          // if specified, credential must satisfy to one of the given restriction.
                 "non_revoked": Optional<<non_revoc_interval>>, // see below,
                                // If specified prover must proof non-revocation
                                // for date in this interval this attribute
                                // (overrides proof level interval)
             }
         predicate_referent: Proof-request local identifier of requested attribute predicate
         predicate_info: Describes requested attribute predicate
             {
                 "name": attribute name, (case insensitive and ignore spaces)
                 "p_type": predicate type (Currently >= only)
                 "p_value": predicate value
                 "restrictions": Optional<[<attr_filter>]> // see below,
                                 // if specified, credential must satisfy to one of the given restriction.
                 "non_revoked": Optional<<non_revoc_interval>>, // see below,
                                // If specified prover must proof non-revocation
                                // for date in this interval this attribute
                                // (overrides proof level interval)
             }
         non_revoc_interval: Defines non-revocation interval
             {
                 "from": Optional<int>, // timestamp of interval beginning
                 "to": Optional<int>, // timestamp of interval ending
             }
    :return: json with credentials for the given pool request.
     {
         "requested_attrs": {
             "<attr_referent>": [{ cred_info: <credential_info>, interval: Optional<non_revoc_interval> }],
             ...,
         },
         "requested_predicates": {
             "requested_predicates": [{ cred_info: <credential_info>, timestamp: Optional<integer> }, { cred_info: <credential_2_info>, timestamp: Optional<integer> }],
             "requested_predicate_2_referent": [{ cred_info: <credential_2_info>, timestamp: Optional<integer> }]
         }
     }, where credential is
     {
         "referent": <string>,
         "attrs": [{"attr_name" : "attr_raw_value"}],
         "cred_def_id": string,
         "rev_reg_id": Optional<int>,
         "cred_rev_id": Optional<int>,
     }
    """

    logger = logging.getLogger(__name__)
    logger.debug("prover_get_credentials_for_proof_req: >>> wallet_handle: %r, proof_request_json: %r",
                 wallet_handle,
                 proof_request_json)

    if not hasattr(prover_get_credentials_for_proof_req, "cb"):
        logger.debug("prover_get_credentials_for_proof_req: Creating callback")
        prover_get_credentials_for_proof_req.cb = create_cb(CFUNCTYPE(None, c_int32, c_int32, c_char_p))

    c_wallet_handle = c_int32(wallet_handle)
    c_proof_request_json = c_char_p(proof_request_json.encode('utf-8'))

    credentials_json = await do_call('indy_prover_get_credentials_for_proof_req',
                                     c_wallet_handle,
                                     c_proof_request_json,
                                     prover_get_credentials_for_proof_req.cb)

    res = credentials_json.decode()
    logger.debug("prover_get_credentials_for_proof_req: <<< res: %r", res)
    return res


async def prover_create_proof(wallet_handle: int,
                              proof_req_json: str,
                              requested_credentials_json: str,
                              master_secret_name: str,
                              schemas_json: str,
                              credential_defs_json: str,
                              rev_states_json: str) -> str:
    """
    Creates a proof according to the given proof request
    Either a corresponding credential with optionally revealed attributes or self-attested attribute must be provided
    for each requested attribute (see indy_prover_get_credentials_for_pool_req).
    A proof request may request multiple credentials from different schemas and different issuers.
    All required schemas, public keys and revocation registries must be provided.
    The proof request also contains nonce.
    The proof contains either proof or self-attested attribute value for each requested attribute.

    :param wallet_handle: wallet handler (created by open_wallet).
    :param proof_req_json: proof request json
         {
             "name": string,
             "version": string,
             "nonce": string,
             "requested_attrs": { // set of requested attributes
                  "<attr_referent>": <attr_info>, // see below
                  ...,
             },
             "requested_predicates": { // set of requested predicates
                  "<predicate_referent>": <predicate_info>, // see below
                  ...,
              },
             "non_revoked": Optional<<non_revoc_interval>>, // see below,
                            // If specified prover must proof non-revocation
                            // for date in this interval for each attribute
    :param requested_credentials_json: either a credential or self-attested attribute for each requested attribute
         {
             "self_attested_attributes": {
                 "self_attested_attribute_referent": string
             },
             "requested_attributes": {
                 "requested_attribute_referent_1": {"cred_id": string, "timestamp": Optional<number>, revealed: <bool> }},
                 "requested_attribute_referent_2": {"cred_id": string, "timestamp": Optional<number>, revealed: <bool> }}
             },
             "requested_predicates": {
                 "requested_predicates_referent_1": {"cred_id": string, "timestamp": Optional<number> }},
             }
         }
    :param schemas_json: all schemas json participating in the proof request
         {
             <schema1_id>: <schema1_json>,
             <schema2_id>: <schema2_json>,
             <schema3_id>: <schema3_json>,
         }
    :param master_secret_name: the name of the master secret stored in the wallet

    :param credential_defs_json: all credential definitions json participating in the proof request
         {
             "credential_def1_id": <credential_def1_json>,
             "credential_def2_id": <credential_def2_json>,
             "credential_def3_id": <credential_def3_json>,
         }
    :param rev_states_json: all revocation states json participating in the proof request
         {
             "rev_reg1_id": {
                 "freshness1": <rev_state1>,
                 "freshness2": <rev_state2>,
             },
             "credential2_referent_in_wallet": {
                 "freshness3": <rev_state3>
             },
             "credential3_referent_in_wallet": {
                 "freshness4": <rev_state4>
             },
         }
    where
     attr_referent: Proof-request local identifier of requested attribute
     attr_info: Describes requested attribute
         {
             "name": string, // attribute name, (case insensitive and ignore spaces)
             "restrictions": Optional<[<attr_filter>]> // see below,
                              // if specified, credential must satisfy to one of the given restriction.
             "non_revoked": Optional<<non_revoc_interval>>, // see below,
                            // If specified prover must proof non-revocation
                            // for date in this interval this attribute
                            // (overrides proof level interval)
         }
     predicate_referent: Proof-request local identifier of requested attribute predicate
     predicate_info: Describes requested attribute predicate
         {
             "name": attribute name, (case insensitive and ignore spaces)
             "p_type": predicate type (Currently >= only)
             "p_value": predicate value
             "restrictions": Optional<[<attr_filter>]> // see below,
                             // if specified, credential must satisfy to one of the given restriction.
             "non_revoked": Optional<<non_revoc_interval>>, // see below,
                            // If specified prover must proof non-revocation
                            // for date in this interval this attribute
                            // (overrides proof level interval)
         }
     non_revoc_interval: Defines non-revocation interval
         {
             "from": Optional<int>, // timestamp of interval beginning
             "to": Optional<int>, // timestamp of interval ending
         }
         
    :return: Proof json
        For each requested attribute either a proof (with optionally revealed attribute value) or
        self-attested attribute value is provided.
        Each proof is associated with a credential and corresponding schema_key, issuer_did and revoc_reg_seq_no.
        There is also aggregated proof part common for all credential proofs.
         {
             "requested": {
                 "revealed_attrs": {
                     "requested_attr1_id": {sub_proof_index: number, raw: string, encoded: string},
                     "requested_attr4_id": {sub_proof_index: number: string, encoded: string},
                 },
                 "unrevealed_attrs": {
                     "requested_attr3_id": {sub_proof_index: number}
                 },
                 "self_attested_attrs": {
                     "requested_attr2_id": self_attested_value,
                 },
                 "requested_predicates": {
                     "requested_predicate_1_referent": {sub_proof_index: int},
                     "requested_predicate_2_referent": {sub_proof_index: int},
                 }
             }
             "proof": {
                 "proofs": [ <credential_proof>, <credential_proof>, <credential_proof> ],
                 "aggregated_proof": <aggregated_proof>
             }
             "identifiers": [{schema_id, cred_def_id, Optional<rev_reg_id>, Optional<timestamp>}]
         }
    """

    logger = logging.getLogger(__name__)
    logger.debug("prover_create_proof: >>> wallet_handle: %r, proof_req_json: %r, requested_credentials_json: %r, "
                 "schemas_json: %r, master_secret_name: %r, credential_defs_json: %r, rev_infos_json: %r",
                 wallet_handle,
                 proof_req_json,
                 requested_credentials_json,
                 schemas_json,
                 master_secret_name,
                 credential_defs_json,
                 rev_states_json)

    if not hasattr(prover_create_proof, "cb"):
        logger.debug("prover_create_proof: Creating callback")
        prover_create_proof.cb = create_cb(CFUNCTYPE(None, c_int32, c_int32, c_char_p))

    c_wallet_handle = c_int32(wallet_handle)
    c_proof_req_json = c_char_p(proof_req_json.encode('utf-8'))
    c_requested_credentials_json = c_char_p(requested_credentials_json.encode('utf-8'))
    c_schemas_json = c_char_p(schemas_json.encode('utf-8'))
    c_master_secret_name = c_char_p(master_secret_name.encode('utf-8'))
    c_credential_defs_json = c_char_p(credential_defs_json.encode('utf-8'))
    c_rev_infos_json = c_char_p(rev_states_json.encode('utf-8'))

    proof_json = await do_call('indy_prover_create_proof',
                               c_wallet_handle,
                               c_proof_req_json,
                               c_requested_credentials_json,
                               c_master_secret_name,
                               c_schemas_json,
                               c_credential_defs_json,
                               c_rev_infos_json,
                               prover_create_proof.cb)

    res = proof_json.decode()
    logger.debug("prover_create_proof: <<< res: %r", res)
    return res


async def verifier_verify_proof(proof_request_json: str,
                                proof_json: str,
                                schemas_json: str,
                                credential_defs_json: str,
                                rev_reg_defs_json: str,
                                rev_regs_json: str) -> bool:
    """
    Verifies a proof (of multiple credential).
    All required schemas, public keys and revocation registries must be provided.

    :param proof_request_json: 
         {
             "name": string,
             "version": string,
             "nonce": string,
             "requested_attrs": { // set of requested attributes
                  "<attr_referent>": <attr_info>, // see below
                  ...,
             },
             "requested_predicates": { // set of requested predicates
                  "<predicate_referent>": <predicate_info>, // see below
                  ...,
              },
             "non_revoked": Optional<<non_revoc_interval>>, // see below,
                            // If specified prover must proof non-revocation
                            // for date in this interval for each attribute
                            // (can be overridden on attribute level)
         }
    :param proof_json: created for request proof json
         {
             "requested": {
                 "revealed_attrs": {
                     "requested_attr1_id": {sub_proof_index: number, raw: string, encoded: string},
                     "requested_attr4_id": {sub_proof_index: number: string, encoded: string},
                 },
                 "unrevealed_attrs": {
                     "requested_attr3_id": {sub_proof_index: number}
                 },
                 "self_attested_attrs": {
                     "requested_attr2_id": self_attested_value,
                 },
                 "requested_predicates": {
                     "requested_predicate_1_referent": {sub_proof_index: int},
                     "requested_predicate_2_referent": {sub_proof_index: int},
                 }
             }
             "proof": {
                 "proofs": [ <credential_proof>, <credential_proof>, <credential_proof> ],
                 "aggregated_proof": <aggregated_proof>
             }
             "identifiers": [{schema_id, cred_def_id, Optional<rev_reg_id>, Optional<timestamp>}]
         }
    :param schemas_json: all schema jsons participating in the proof
         {
             <schema1_id>: <schema1_json>,
             <schema2_id>: <schema2_json>,
             <schema3_id>: <schema3_json>,
         }
    :param credential_defs_json: all credential definitions json participating in the proof
         {
             "credential_def1_id": <credential_def1_json>,
             "credential_def2_id": <credential_def2_json>,
             "credential_def3_id": <credential_def3_json>,
         }
    :param rev_reg_defs_json: all revocation registry definitions json participating in the proof
         {
             "rev_reg_def1_id": <rev_reg_def1_json>,
             "rev_reg_def2_id": <rev_reg_def2_json>,
             "rev_reg_def3_id": <rev_reg_def3_json>,
         }
    :param rev_regs_json: all revocation registries json participating in the proof
         {
             "rev_reg1_id": {
                 "freshness1": <rev_reg1>,
                 "freshness2": <rev_reg2>,
             },
             "credential2_referent_in_wallet": {
                 "freshness3": <rev_reg3>
             },
             "credential3_referent_in_wallet": {
                 "freshness4": <rev_reg4>
             },
         }
    :return: valid: true - if signature is valid, false - otherwise
    """

    logger = logging.getLogger(__name__)
    logger.debug("verifier_verify_proof: >>> proof_request_json: %r, proof_json: %r, schemas_json: %r, "
                 "credential_defs_jsons: %r, rev_reg_defs_json: %r, rev_regs_json: %r",
                 proof_request_json,
                 proof_json,
                 schemas_json,
                 credential_defs_json,
                 rev_reg_defs_json,
                 rev_regs_json)

    if not hasattr(verifier_verify_proof, "cb"):
        logger.debug("verifier_verify_proof: Creating callback")
        verifier_verify_proof.cb = create_cb(CFUNCTYPE(None, c_int32, c_int32, c_bool))

    c_proof_request_json = c_char_p(proof_request_json.encode('utf-8'))
    c_proof_json = c_char_p(proof_json.encode('utf-8'))
    c_schemas_json = c_char_p(schemas_json.encode('utf-8'))
    c_credential_defs_json = c_char_p(credential_defs_json.encode('utf-8'))
    c_rev_reg_defs_json = c_char_p(rev_reg_defs_json.encode('utf-8'))
    c_rev_regs_json = c_char_p(rev_regs_json.encode('utf-8'))

    res = await do_call('indy_verifier_verify_proof',
                        c_proof_request_json,
                        c_proof_json,
                        c_schemas_json,
                        c_credential_defs_json,
                        c_rev_reg_defs_json,
                        c_rev_regs_json,
                        verifier_verify_proof.cb)

    logger.debug("verifier_verify_proof: <<< res: %r", res)
    return res


async def create_revocation_state(blob_storage_reader_handle: int,
                                  rev_reg_def_json: str,
                                  rev_reg_delta_json: str,
                                  timestamp: int,
                                  cred_rev_id: str) -> str:
    logger = logging.getLogger(__name__)
    logger.debug("create_revocation_info: >>> blob_storage_reader_handle: %r, rev_reg_def_json: %r,"
                 " rev_reg_delta_json: %r, timestamp: %r, cred_rev_id: %r",
                 blob_storage_reader_handle,
                 rev_reg_def_json,
                 rev_reg_delta_json,
                 timestamp,
                 cred_rev_id)

    if not hasattr(create_revocation_state, "cb"):
        logger.debug("create_revocation_state: Creating callback")
        create_revocation_state.cb = create_cb(CFUNCTYPE(None, c_int32, c_int32, c_char_p))

    c_blob_storage_reader_handle = c_int32(blob_storage_reader_handle)
    c_rev_reg_def_json = c_char_p(rev_reg_def_json.encode('utf-8'))
    c_rev_reg_delta_json = c_char_p(rev_reg_delta_json.encode('utf-8'))
    c_timestamp = c_uint64(timestamp)
    c_cred_rev_id = c_char_p(cred_rev_id.encode('utf-8'))

    rev_state_json = await do_call('indy_create_revocation_state',
                                   c_blob_storage_reader_handle,
                                   c_rev_reg_def_json,
                                   c_rev_reg_delta_json,
                                   c_timestamp,
                                   c_cred_rev_id,
                                   create_revocation_state.cb)

    res = rev_state_json.decode()
    logger.debug("create_revocation_state: <<< res: %r", res)
    return res


async def update_revocation_state(blob_storage_reader_handle: int,
                                  rev_state_json: str,
                                  rev_reg_def_json: str,
                                  rev_reg_delta_json: str,
                                  timestamp: int,
                                  cred_rev_id: str) -> str:
    logger = logging.getLogger(__name__)
    logger.debug("update_revocation_state: >>> blob_storage_reader_handle: %r, rev_state_json: %r, "
                 "rev_reg_def_json: %r, rev_reg_delta_json: %r, timestamp: %r, cred_rev_id: %r",
                 blob_storage_reader_handle,
                 rev_state_json,
                 rev_reg_def_json,
                 rev_reg_delta_json,
                 timestamp,
                 cred_rev_id)

    if not hasattr(update_revocation_state, "cb"):
        logger.debug("update_revocation_state: Creating callback")
        update_revocation_state.cb = create_cb(CFUNCTYPE(None, c_int32, c_int32, c_char_p))

    c_blob_storage_reader_handle = c_int32(blob_storage_reader_handle)
    c_rev_state_json = c_char_p(rev_state_json.encode('utf-8'))
    c_rev_reg_def_json = c_char_p(rev_reg_def_json.encode('utf-8'))
    c_rev_reg_delta_json = c_char_p(rev_reg_delta_json.encode('utf-8'))
    c_timestamp = c_uint64(timestamp)
    c_cred_rev_id = c_char_p(cred_rev_id.encode('utf-8'))

    updated_rev_state_json = await do_call('indy_update_revocation_state',
                                           c_blob_storage_reader_handle,
                                           c_rev_state_json,
                                           c_rev_reg_def_json,
                                           c_rev_reg_delta_json,
                                           c_timestamp,
                                           c_cred_rev_id,
                                           update_revocation_state.cb)

    res = updated_rev_state_json.decode()
    logger.debug("update_revocation_state: <<< res: %r", res)
    return res
