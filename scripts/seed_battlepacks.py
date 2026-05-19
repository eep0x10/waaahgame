"""Seed Battlepack scenarios. Idempotent (upsert)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BATTLEPACKS_DATA = [
    # AoS Vanguard
    {
        'system_code': 'aos4',
        'slug': 'aos-vanguard-first-blood',
        'name': 'Primeiro Sangue',
        'format': 'vanguard',
        'summary': 'Um confronto veloz onde duas hostes se chocam em campo aberto. Quem conquista o terreno primeiro vence o dia.',
        'primary_objective': 'Marque 2 VP ao fim de cada battle round para cada marcador de objetivo que você controla. O jogador que controlar mais objetivos ao fim da rodada 5 marca 5 VP adicionais.',
        'secondary_objectives': [
            'Abater o Warlord: Marque 3 VP se o general inimigo for destruído.',
            'Primeiro Golpe: Marque 2 VP se você destruir uma unidade inimiga no primeiro battle round.',
            'Segurar o Flanco: Marque 1 VP ao fim de cada rodada em que você controla o objetivo na zona de implantação do oponente.',
        ],
        'deployment_text': 'Coloque objetivos no centro e nos flancos esquerdo e direito, a 9" da linha central. Cada jogador implanta a até 12" da borda da mesa.',
        'special_rules_text': 'Ambos os jogadores fazem um roll-off; o vencedor escolhe qual jogador implanta e toma o primeiro turno. Triumph rolls se aplicam conforme as Regras Principais.',
    },
    {
        'system_code': 'aos4',
        'slug': 'aos-vanguard-the-vice',
        'name': 'O Torno',
        'format': 'vanguard',
        'summary': 'Duas forças avançam de lados opostos, cada uma tentando cercar a outra. Mobilidade e agressividade decidem esta batalha.',
        'primary_objective': 'Marque 3 VP ao fim de cada battle round para cada objetivo que você controla dentro do território do oponente. Marque 1 VP para cada objetivo no seu próprio território.',
        'secondary_objectives': [
            'Glória ou Morte: Marque 3 VP se você vencer um combate contra uma unidade inimiga com mais de 10 modelos.',
            'Cercar: Marque 2 VP se você tiver pelo menos uma unidade na zona de implantação inimiga ao fim da rodada 3.',
            'Negar Terreno: Marque 1 VP ao fim de cada rodada em que o inimigo não controla nenhum objetivo no seu território.',
        ],
        'deployment_text': 'Os objetivos são colocados em padrão diagonal pelo tabuleiro. Os jogadores se implantam em cantos opostos dentro de um triângulo de 12".',
        'special_rules_text': 'Regra da Pinça: Unidades que iniciam uma ação de carga a até 3" de uma unidade amiga ganham +1 na rolagem de carga.',
    },
    {
        'system_code': 'aos4',
        'slug': 'aos-vanguard-hold-the-center',
        'name': 'Segurar o Centro',
        'format': 'vanguard',
        'summary': 'Uma relíquia central atrai ambas as forças para uma luta de desgaste. Nenhum lado pode se dar ao luxo de ceder o meio-campo.',
        'primary_objective': 'Coloque um objetivo no centro exato do campo de batalha. Marque 4 VP ao fim de cada battle round em que você o controla. Marque 2 VP ao fim de cada rodada em que você o contesta.',
        'secondary_objectives': [
            'Defensor do Reino: Marque 3 VP se você controlar o objetivo central por três rodadas consecutivas.',
            'Conter o Avanço: Marque 2 VP se você destruir mais unidades inimigas do que perder em uma única rodada.',
            'Terra Sagrada: Marque 1 VP a cada rodada em que nenhum modelo inimigo esteja a até 6" do objetivo central.',
        ],
        'deployment_text': 'Os jogadores se implantam nas bordas longas opostas a até 6". Um único objetivo é colocado no centro do tabuleiro.',
        'special_rules_text': 'O objetivo central é contestado se ambos os jogadores tiverem uma unidade a até 3" dele ao fim de uma rodada; nenhum jogador marca VP primário nesse caso.',
    },
    # AoS Battlehost
    {
        'system_code': 'aos4',
        'slug': 'aos-battlehost-battlelines-drawn',
        'name': 'Linhas de Batalha',
        'format': 'battlehost',
        'summary': 'Duas hostes completamente reunidas se enfrentam numa frente ampla. O desgaste e a maestria tática determinam o vencedor.',
        'primary_objective': 'Cinco objetivos são colocados pelo tabuleiro. Marque 2 VP por objetivo controlado ao fim de cada rodada. Marque 3 VP adicionais se controlar três ou mais.',
        'secondary_objectives': [
            'Aniquilação: Marque 1 VP para cada unidade inimiga que você destruir, máximo de 6 VP.',
            'Romper a Linha: Marque 4 VP se você tiver uma unidade na zona de implantação inimiga ao fim da rodada 4 ou 5.',
            'Reunir o Estandarte: Marque 2 VP se uma unidade com a palavra-chave Leader segurar um objetivo por duas rodadas consecutivas.',
        ],
        'deployment_text': 'Os jogadores se implantam em suas respectivas metades a até 12" da borda. Os objetivos são colocados no centro e a 12" de cada borda curta na linha média, mais um em cada zona de implantação.',
        'special_rules_text': 'As Grandes Táticas se aplicam. Cada jogador seleciona uma Grande Tática no início do jogo entre as disponíveis para sua facção.',
    },
    {
        'system_code': 'aos4',
        'slug': 'aos-battlehost-tooth-and-nail',
        'name': 'Dente e Garra',
        'format': 'battlehost',
        'summary': 'Uma briga brutal de curto alcance sem trégua. Força bruta e determinação ganham o dia.',
        'primary_objective': 'Marque 3 VP ao fim de cada rodada para cada objetivo que você controla. Objetivos só podem ser capturados por unidades que combateram nesta rodada.',
        'secondary_objectives': [
            'Ímpeto Selvagem: Marque 3 VP se você carregar e destruir uma unidade inimiga na mesma rodada.',
            'Sem Recuo: Marque 2 VP a cada rodada em que você tiver mais modelos na metade inimiga do que o oponente.',
            'Contagem do Açougueiro: Marque 1 VP para cada 5 ferimentos que você infligir, máximo de 5 VP no total.',
        ],
        'deployment_text': 'O tabuleiro é dividido em três faixas. Os jogadores se implantam a até 6" da borda; todos os objetivos ficam a até 6" da faixa central.',
        'special_rules_text': 'Todas as cargas neste cenário ganham a palavra-chave Savage. Unidades que carregam com sucesso somam 1 às rolagens de ataque até o fim da fase de combate.',
    },
    # 40k Strike Force
    {
        'system_code': 'w40k10',
        'slug': '40k-strike-force-take-and-hold',
        'name': 'Tomar e Segurar',
        'format': 'strike_force',
        'summary': 'Ambas as forças correm para capturar e manter locais estratégicos. Quem controlar mais terreno ao fim da batalha reivindica a supremacia.',
        'primary_objective': 'Marque 4 VP ao fim de sua fase de Comando para cada marcador de objetivo que você controla, mais 5 VP ao fim da batalha por cada objetivo que você controla.',
        'secondary_objectives': [
            'Engajar em Todas as Frentes: Marque 3 VP ao fim de cada rodada em que você tiver unidades em pelo menos três setores diferentes do tabuleiro.',
            'Recuperar Dados do Campo: Marque 4 VP cada vez que uma de suas unidades executa esta ação em um objetivo que você controla.',
            'Tomar Objetivo Hostil: Marque 3 VP na primeira vez que você capturar um objetivo que estava sob controle inimigo.',
        ],
        'deployment_text': 'Implantação padrão conforme as regras de Strike Force. Quatro objetivos colocados na linha média em intervalos, mais um em cada zona de implantação.',
        'special_rules_text': 'Reservas Táticas: até metade do seu exército pode ser mantida em Reservas Estratégicas. Unidades chegando de reserva não podem pontuar objetivos no turno em que chegam.',
    },
    {
        'system_code': 'w40k10',
        'slug': '40k-strike-force-scorched-earth',
        'name': 'Terra Arrasada',
        'format': 'strike_force',
        'summary': 'Em vez de capturar objetivos intactos, cada lado busca negá-los ao inimigo pela destruição. Uma luta de atrito pírrico.',
        'primary_objective': 'Marque 5 VP ao fim da batalha para cada objetivo que você controla. Marque 3 VP cada vez que você destruir um objetivo na metade do oponente.',
        'secondary_objectives': [
            'Especialista em Demolição: Marque 4 VP na primeira vez que você destruir dois ou mais objetivos em uma única rodada.',
            'Última Resistência: Marque 3 VP se pelo menos uma de suas unidades sobreviver na zona de implantação inimiga ao fim da rodada 5.',
            'Sangue e Fogo: Marque 2 VP a cada rodada em que você destruir pelo menos uma unidade inimiga.',
        ],
        'deployment_text': 'Implantação diagonal; os jogadores se posicionam em cantos opostos dentro de triângulos de 12". Objetivos colocados ao longo da linha central e no meio-campo.',
        'special_rules_text': 'Objetivos podem ser destruídos por uma unidade em contato de base gastando 1 CP e realizando uma ação Demolir. Objetivos destruídos são removidos.',
    },
    {
        'system_code': 'w40k10',
        'slug': '40k-strike-force-tipping-point',
        'name': 'Ponto de Virada',
        'format': 'strike_force',
        'summary': 'Uma batalha de ímpeto. Capture objetivos-chave para mudar o equilíbrio e segure-os tempo suficiente para reivindicar a vitória.',
        'primary_objective': 'Marque 3 VP ao fim de sua fase de Comando para cada objetivo. Marque 3 VP bônus se você controlar mais objetivos do que o oponente.',
        'secondary_objectives': [
            'Golpe Cirúrgico: Marque 4 VP na primeira vez que você destruir uma unidade Character inimiga.',
            'Dominação: Marque 3 VP ao fim de cada rodada em que você controla todos os objetivos na sua zona de implantação e pelo menos um objetivo na zona inimiga.',
            'Avanço Incessante: Marque 2 VP por cada rodada em que uma unidade selecionada termina a fase de Movimento mais distante da sua borda de implantação do que na rodada anterior.',
        ],
        'deployment_text': 'Implantação padrão pela borda longa a até 12". Cinco objetivos: um no centro, dois nos flancos do meio-campo, um em cada zona de implantação.',
        'special_rules_text': 'Regra do Ponto de Virada: qualquer objetivo mantido pelo mesmo jogador por três rodadas consecutivas torna-se um Ponto Fortificado valendo VP dobrado até o fim do jogo.',
    },
    # 40k Combat Patrol
    {
        'system_code': 'w40k10',
        'slug': '40k-combat-patrol-clash',
        'name': 'Confronto de Patrulha',
        'format': 'combat_patrol',
        'summary': 'Uma escaramuça de movimento rápido entre forças leves. Velocidade e astúcia importam mais do que poder de fogo bruto.',
        'primary_objective': 'Marque 3 VP ao fim de cada rodada para cada objetivo que você controla. Marque 2 VP se você controlar mais do que o oponente.',
        'secondary_objectives': [
            'Reconhecimento: Marque 3 VP se uma unidade terminar seu movimento dentro da zona de implantação inimiga.',
            'Eliminar a Ameaça: Marque 3 VP na primeira vez que você destruir uma unidade inimiga com 3 ou mais modelos.',
            'Assegurar a Área: Marque 2 VP a cada rodada em que você controla o objetivo central.',
        ],
        'deployment_text': 'Implantação pela borda curta a até 9" da borda da mesa. Três objetivos: um central, um em cada metade do tabuleiro na linha média.',
        'special_rules_text': 'Velocidade de Patrulha: todas as unidades de infantaria ganham +1" de movimento durante a batalha. As fichas de Combat Patrol se aplicam.',
    },
]


def _do_seed(db, GameSystem, Battlepack):
    created = 0
    updated = 0
    for data in BATTLEPACKS_DATA:
        gs = GameSystem.query.filter_by(code=data['system_code']).first()
        if not gs:
            continue
        existing = Battlepack.query.filter_by(slug=data['slug']).first()
        if existing:
            existing.name = data['name']
            existing.format = data['format']
            existing.summary = data['summary']
            existing.primary_objective = data['primary_objective']
            existing.secondary_objectives_json = data['secondary_objectives']
            existing.deployment_text = data['deployment_text']
            existing.special_rules_text = data['special_rules_text']
            updated += 1
        else:
            bp = Battlepack(
                system_id=gs.id,
                slug=data['slug'],
                name=data['name'],
                format=data['format'],
                summary=data['summary'],
                primary_objective=data['primary_objective'],
                secondary_objectives_json=data['secondary_objectives'],
                deployment_text=data['deployment_text'],
                special_rules_text=data['special_rules_text'],
            )
            db.session.add(bp)
            created += 1
    db.session.commit()
    return created, updated


if __name__ == '__main__':
    from app import create_app
    from app.extensions import db
    from app.models.game import GameSystem
    from app.models.battlepack import Battlepack

    app = create_app('dev')
    with app.app_context():
        n_created, n_updated = _do_seed(db, GameSystem, Battlepack)
        print(f'Seeded {n_created} battlepacks, updated {n_updated}.')
