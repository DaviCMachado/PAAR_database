CREATE VIEW vw_pessoa_localizacao AS
SELECT 
    p.id AS pessoa_id,
    p.sexo,
    p.forca,
    p.posto_graduacao,
    l.estado,
    l.cidade
FROM Pessoa p
JOIN Localizacao l ON p.id = l.id;

CREATE VIEW vw_pessoa_esporte AS
SELECT 
    p.id AS pessoa_id,
    p.sexo,
    p.forca,
    p.posto_graduacao,
    e.modalidade,
    e.possui_medalha,
    e.possui_bolsa,
    e.paar
FROM Pessoa p
JOIN Esporte e ON p.id = e.id;

CREATE VIEW vw_esporte AS
SELECT 
    e.id AS esporte_id,
    e.modalidade,
    e.possui_medalha,
    e.possui_bolsa,
    e.paar
FROM Esporte e;

DELIMITER //

CREATE TRIGGER trg_validate_modalidade
BEFORE INSERT ON Esporte
FOR EACH ROW
BEGIN
    IF NEW.modalidade NOT IN (
        'Apneia', 'Atletismo', 'Basquete', 'Boxe', 'Canoagem Slalom', 
        'Canoagem Velocidade', 'Ciclismo MTB', 'Escalada Esportiva', 'Esgrima', 
        'Futebol', 'Ginastica Artistica', 'Golfe', 'Judo', 'Levantamento de Peso', 
        'Lifesaving', 'Lutas Associadas (Wrestling)', 'Maratona', 'Maratonas Aquaticas', 
        'Nado Sincronizado', 'Natacao', 'Orientacao', 'Paraquedismo', 'Pentatlo Militar', 
        'Pentatlo Moderno', 'Pentatlo Naval', 'Pesca Submarina', 'Taekwondo', 'Tiro', 
        'Tiro com Arco', 'Triatlo', 'Vela', 'Voleibol', 'Volei de Praia'
    ) THEN
        SIGNAL SQLSTATE '45000' 
        SET MESSAGE_TEXT = 'Modalidade inválida. Insira uma modalidade válida!';
    END IF;
END;

//

DELIMITER ;

SELECT * FROM vw_pessoa_localizacao;
SELECT * FROM vw_esporte;
SELECT * FROM vw_pessoa_esporte;

INSERT INTO Esporte (modalidade, possui_medalha, possui_bolsa, paar)
VALUES ('Xadrez', 'Não', 'Não', 'Não'); -- Deve falhar
