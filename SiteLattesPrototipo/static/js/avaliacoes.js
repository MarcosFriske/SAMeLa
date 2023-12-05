function desinscreverEvento(avaliacao_id) {
    if (confirm("Tem certeza de que deseja desinscrever deste evento?")) {
        const form = document.createElement('form');
        form.method = 'post';
        form.action = '/desinscrever_evento/' + avaliacao_id;

        document.body.appendChild(form);
        form.submit();
    }
}