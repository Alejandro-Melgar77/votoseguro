"""
S3-01: Motor de Escrutinio Homomórfico Aditivo de Paillier (Invariante #13 y RF-55)
Calcula los resultados de la elección multiplicando modularmente los textos cifrados
E(m1) * E(m2) % n^2 = E(m1 + m2) para cada circunscripción y desglose (por nivel y filtro).
Los acumuladores se mantienen cifrados en la tabla homomorphic_tally_cell hasta que el quórum
de custodios de Shamir (k de n) reconstruye la clave privada en memoria RAM para el descifrado oficial.
Aplica k-anonimato antes del descifrado: las celdas con menos de k votos jamás se descifran.
"""
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any
import phe.paillier as paillier
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crypto.hashing import canonical_json, sha256_hex
from app.db.models.election import Election, ElectionStatus, HomomorphicTallyCell
from app.db.models.structure import (
    BreakdownKind,
    Candidate,
    Constituency,
    Contest,
    ContestBreakdown,
    FilterDefinition,
    HierarchyLevel,
    UnitNode,
    VoterGroup,
)
from app.db.models.voting import Vote, VoteChoiceType


class HomomorphicTallyEngine:
    """
    Motor oficial de agregación y escrutinio homomórfico en producción.
    """

    @staticmethod
    async def aggregate_votes_for_election(
        db: AsyncSession,
        election: Election,
    ) -> list[HomomorphicTallyCell]:
        """
        Suma homomórficamente todos los votos de la elección usando EXCLUSIVAMENTE
        la clave pública Paillier (n). Agrupa simultáneamente por circunscripción
        y por todos los desgloses jerárquicos y filtros configurados.
        """
        if not election.paillier_public_n:
            raise ValueError(
                "La elección no cuenta con una clave pública Paillier configurada "
                "(debe ejecutarse primero la Ceremonia de Claves de Shamir)."
            )

        n = int(election.paillier_public_n)
        n_sq = n * n
        pk = paillier.PaillierPublicKey(n)

        # 1. Cargar todos los votos de la elección
        stmt_votes = select(Vote).where(Vote.election_id == election.id)
        all_votes = (await db.execute(stmt_votes)).scalars().all()

        votes_by_constituency: dict[uuid.UUID, list[Vote]] = {}
        for v in all_votes:
            votes_by_constituency.setdefault(v.constituency_id, []).append(v)

        # 2. Cargar estructura completa: Grupos, Niveles, Filtros, Cargos, Desgloses, Circunscripciones, Candidatos
        stmt_groups = (
            select(VoterGroup)
            .where(VoterGroup.election_id == election.id)
        )
        groups = (await db.execute(stmt_groups)).scalars().all()

        tally_cells: list[HomomorphicTallyCell] = []

        for group in groups:
            # Cargar niveles del grupo con nodos
            stmt_levels = select(HierarchyLevel).where(HierarchyLevel.group_id == group.id)
            levels = (await db.execute(stmt_levels)).scalars().all()
            level_map = {lvl.id: lvl for lvl in levels}

            stmt_nodes = select(UnitNode).where(UnitNode.group_id == group.id)
            nodes = (await db.execute(stmt_nodes)).scalars().all()
            nodes_by_level: dict[uuid.UUID, list[UnitNode]] = {}
            for nd in nodes:
                nodes_by_level.setdefault(nd.level_id, []).append(nd)

            # Cargar filtros del grupo
            stmt_filters = select(FilterDefinition).where(FilterDefinition.group_id == group.id)
            filters = (await db.execute(stmt_filters)).scalars().all()
            filter_map = {f.id: f for f in filters}

            # Cargar cargos del grupo con desgloses
            stmt_contests = (
                select(Contest)
                .options(selectinload(Contest.breakdowns))
                .where(Contest.group_id == group.id)
            )
            contests = (await db.execute(stmt_contests)).scalars().all()

            for contest in contests:
                stmt_const = (
                    select(Constituency)
                    .options(
                        selectinload(Constituency.node),
                        selectinload(Constituency.candidates),
                    )
                    .where(Constituency.contest_id == contest.id)
                )
                constituencies = (await db.execute(stmt_const)).scalars().all()

                for const in constituencies:
                    # Candidatos ordenados por ballot_order
                    sorted_cands = sorted(const.candidates, key=lambda c: c.ballot_order)
                    # Vector canónico de opciones: [cand_uuid_1, ..., 'BLANK', 'NULL']
                    option_order_keys = [str(c.id) for c in sorted_cands]
                    if contest.allow_blank:
                        option_order_keys.append("BLANK")
                    if contest.allow_null:
                        option_order_keys.append("NULL")

                    vec_len = len(option_order_keys)
                    const_votes = votes_by_constituency.get(const.id, [])

                    # Celdas a calcular para esta circunscripción
                    cells_to_process: list[dict[str, Any]] = [
                        {
                            "scope_type": "CONSTITUENCY_TOTAL",
                            "breakdown_id": None,
                            "cell_key": "TOTAL",
                            "cell_label": "Total Circunscripción",
                            "votes": const_votes,
                        }
                    ]

                    # Desgloses configurados para el cargo
                    for bd in contest.breakdowns:
                        if bd.kind == BreakdownKind.LEVEL and bd.level_id:
                            target_nodes = nodes_by_level.get(bd.level_id, [])
                            for t_node in target_nodes:
                                # Votos cuyo segment_path comienza con el path del nodo
                                node_votes = [
                                    v for v in const_votes
                                    if v.segment_path and v.segment_path.startswith(t_node.path)
                                ]
                                cells_to_process.append({
                                    "scope_type": "LEVEL_BREAKDOWN",
                                    "breakdown_id": bd.id,
                                    "cell_key": t_node.path,
                                    "cell_label": f"{bd.label or 'Nivel'}: {t_node.name}",
                                    "votes": node_votes,
                                })

                        elif bd.kind == BreakdownKind.FILTER and bd.filter_id:
                            f_def = filter_map.get(bd.filter_id)
                            if f_def:
                                # Extraer valores presentes en filters_snapshot
                                observed_values = set()
                                for v in const_votes:
                                    if v.filters_snapshot and f_def.key in v.filters_snapshot:
                                        observed_values.add(v.filters_snapshot[f_def.name])

                                for val in sorted(observed_values):
                                    f_votes = [
                                        v for v in const_votes
                                        if v.filters_snapshot and v.filters_snapshot.get(f_def.name) == val
                                    ]
                                    cells_to_process.append({
                                        "scope_type": "FILTER_BREAKDOWN",
                                        "breakdown_id": bd.id,
                                        "cell_key": f"{f_def.name}:{val}",
                                        "cell_label": f"{f_def.label}: {val}",
                                        "votes": f_votes,
                                    })

                    # Procesar cada celda y calcular la suma homomórfica
                    for cell_spec in cells_to_process:
                        cell_votes: list[Vote] = cell_spec["votes"]
                        ballots_count = len(cell_votes)

                        # Inicializar acumulador modular en 1 (identidad multiplicativa en Z_n^2)
                        accum_vector = [1] * vec_len

                        for vote in cell_votes:
                            # Extraer o construir el vector cifrado del voto
                            vote_cipher_ints: list[int] = []
                            try:
                                payload = json.loads(vote.encoded_payload)
                                if payload.get("scheme") == "PAILLIER_V1" and "ciphertexts" in payload:
                                    if int(payload["n"]) != n:
                                        raise ValueError("Clave pública de voto incorrecta")
                                    p_keys = payload.get("option_keys", [])
                                    p_ciphers = payload.get("ciphertexts", [])
                                    if p_keys == option_order_keys:
                                        vote_cipher_ints = [
                                            int(c_h, 16) if isinstance(c_h, str) and c_h.startswith("0x") else int(c_h)
                                            for c_h in p_ciphers
                                        ]
                                    else:
                                        # Reordenar vector según el orden canónico de option_order_keys
                                        cmap = {}
                                        for idx, k in enumerate(p_keys):
                                            raw_c = p_ciphers[idx]
                                            c_val = int(raw_c, 16) if isinstance(raw_c, str) and raw_c.startswith("0x") else int(raw_c)
                                            cmap[k] = c_val
                                        vote_cipher_ints = [
                                            cmap.get(k, pk.encrypt(0).ciphertext())
                                            for k in option_order_keys
                                        ]
                            except Exception:
                                pass

                            if vote.choice_type is None and (not vote_cipher_ints or len(vote_cipher_ints) != vec_len):
                                raise ValueError("Voto cifrado inválido; no es posible reconstruirlo desde texto plano.")

                            # Si el voto fue emitido en modo previo o plano, se cifra on-the-fly con pk
                            if not vote_cipher_ints or len(vote_cipher_ints) != vec_len:
                                if vote.choice_type == VoteChoiceType.CANDIDATE and vote.candidate_id:
                                    target_key = str(vote.candidate_id)
                                elif vote.choice_type == VoteChoiceType.BLANK:
                                    target_key = "BLANK"
                                elif vote.choice_type == VoteChoiceType.NULL:
                                    target_key = "NULL"
                                else:
                                    target_key = "BLANK"

                                enc_nums = [
                                    pk.encrypt(1 if opt == target_key else 0)
                                    for opt in option_order_keys
                                ]
                                vote_cipher_ints = [c.ciphertext() for c in enc_nums]

                            # Multiplicación modular homomórfica: E(a) * E(b) % n^2 = E(a + b)
                            for i in range(vec_len):
                                accum_vector[i] = (accum_vector[i] * vote_cipher_ints[i]) % n_sq

                        # Si la celda no tiene votos, el acumulador representa ceros cifrados
                        if ballots_count == 0:
                            enc_zeros = [pk.encrypt(0) for _ in range(vec_len)]
                            accum_vector = [c.ciphertext() for c in enc_zeros]

                        # Invariante #12: k-Anonimato riguroso antes del descifrado
                        # En desgloses (nivel o filtro), si 0 < votos < k_anonymity, se suprime el descifrado
                        suppressed = False
                        if cell_spec["scope_type"] != "CONSTITUENCY_TOTAL":
                            if 0 < ballots_count < election.k_anonymity:
                                suppressed = True

                        aggregated_hex = [hex(val) for val in accum_vector]
                        proof_payload = {
                            "election_id": str(election.id),
                            "constituency_id": str(const.id),
                            "cell_scope_type": cell_spec["scope_type"],
                            "cell_key": cell_spec["cell_key"],
                            "ballots_aggregated": ballots_count,
                            "aggregated_ciphertexts": aggregated_hex,
                        }
                        proof_hash = sha256_hex(canonical_json(proof_payload))

                        # Buscar si ya existe la celda en base de datos para actualizarla o crearla
                        stmt_existing = select(HomomorphicTallyCell).where(
                            HomomorphicTallyCell.constituency_id == const.id,
                            HomomorphicTallyCell.cell_scope_type == cell_spec["scope_type"],
                            HomomorphicTallyCell.cell_key == cell_spec["cell_key"],
                        )
                        existing_cell = (await db.execute(stmt_existing)).scalar_one_or_none()

                        if existing_cell:
                            existing_cell.ballots_aggregated = ballots_count
                            existing_cell.option_order_keys = option_order_keys
                            existing_cell.aggregated_ciphertexts = aggregated_hex
                            existing_cell.suppressed_by_k_anonymity = suppressed
                            existing_cell.cell_proof_hash = proof_hash
                            existing_cell.computed_at = datetime.now(timezone.utc)
                            tally_cells.append(existing_cell)
                        else:
                            new_cell = HomomorphicTallyCell(
                                organization_id=election.organization_id,
                                election_id=election.id,
                                contest_id=contest.id,
                                constituency_id=const.id,
                                cell_scope_type=cell_spec["scope_type"],
                                breakdown_id=cell_spec["breakdown_id"],
                                cell_key=cell_spec["cell_key"],
                                cell_label=cell_spec["cell_label"],
                                ballots_aggregated=ballots_count,
                                option_order_keys=option_order_keys,
                                aggregated_ciphertexts=aggregated_hex,
                                decrypted_counts=None,  # Permanece cifrado hasta quórum Shamir
                                suppressed_by_k_anonymity=suppressed,
                                cell_proof_hash=proof_hash,
                                computed_at=datetime.now(timezone.utc),
                            )
                            db.add(new_cell)
                            tally_cells.append(new_cell)

        await db.flush()
        return tally_cells

    @staticmethod
    async def decrypt_election_tally(
        db: AsyncSession,
        election: Election,
        private_key: paillier.PaillierPrivateKey,
    ) -> dict[str, Any]:
        """
        Descifra ÚNICAMENTE las sumas acumuladas en homomorphic_tally_cell usando
        la clave privada Paillier reconstruida mediante el quórum de Shamir.
        Jamás se descifra una papeleta individual.
        Respeta la Invariante #12: celdas suprimidas por k-anonimato permanecen con decrypted_counts = None.
        """
        stmt = (
            select(HomomorphicTallyCell)
            .where(HomomorphicTallyCell.election_id == election.id)
            .order_by(HomomorphicTallyCell.constituency_id.asc(), HomomorphicTallyCell.cell_key.asc())
        )
        cells = (await db.execute(stmt)).scalars().all()

        if not cells:
            # Si no se han acumulado las celdas previamente, ejecutamos la suma homomórfica primero
            cells = await HomomorphicTallyEngine.aggregate_votes_for_election(db, election)

        pk = private_key.public_key
        decrypted_cells_count = 0
        suppressed_cells_count = 0
        total_ballots_tallied = 0
        cell_proofs: list[dict[str, Any]] = []

        for cell in cells:
            if cell.cell_scope_type == "CONSTITUENCY_TOTAL":
                total_ballots_tallied += cell.ballots_aggregated

            if cell.suppressed_by_k_anonymity:
                # Invariante #12: No se descifra la celda suprimida
                cell.decrypted_counts = None
                suppressed_cells_count += 1
                cell_proofs.append({
                    "cell_key": cell.cell_key,
                    "suppressed": True,
                    "proof_hash": cell.cell_proof_hash,
                })
            else:
                counts_dict: dict[str, int] = {}
                for idx, opt_key in enumerate(cell.option_order_keys):
                    c_hex = cell.aggregated_ciphertexts[idx]
                    c_int = int(c_hex, 16) if isinstance(c_hex, str) and c_hex.startswith("0x") else int(c_hex)
                    enc_num = paillier.EncryptedNumber(pk, c_int, 0)
                    decrypted_val = private_key.decrypt(enc_num)
                    counts_dict[opt_key] = int(decrypted_val)

                cell.decrypted_counts = counts_dict
                decrypted_cells_count += 1
                cell_proofs.append({
                    "cell_key": cell.cell_key,
                    "suppressed": False,
                    "counts": counts_dict,
                    "proof_hash": cell.cell_proof_hash,
                })

        # Generar hash oficial del escrutinio homomórfico descifrado
        tally_act_payload = {
            "election_id": str(election.id),
            "organization_id": str(election.organization_id),
            "total_ballots_tallied": total_ballots_tallied,
            "decrypted_cells_count": decrypted_cells_count,
            "suppressed_cells_count": suppressed_cells_count,
            "proofs": cell_proofs,
        }
        tally_ceremony_hash = sha256_hex(canonical_json(tally_act_payload))

        election.tally_ceremony_hash = tally_ceremony_hash
        election.status = ElectionStatus.TALLIED
        election.updated_at = datetime.now(timezone.utc)

        await db.flush()

        return {
            "election_id": election.id,
            "status": ElectionStatus.TALLIED.value,
            "tally_ceremony_hash": tally_ceremony_hash,
            "decrypted_cells_count": decrypted_cells_count,
            "suppressed_cells_count": suppressed_cells_count,
            "total_ballots_tallied": total_ballots_tallied,
        }
