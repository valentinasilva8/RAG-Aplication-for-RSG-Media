create table
  public.chunks (
    id serial not null,
    element_id text not null,
    text text not null,
    document_id integer null,
    filetype text null,
    languages text[] null,
    start_page_number integer null,
    end_page_number integer null,
    orig_elements text null,
    embedding public.vector null,
    source_file text null,
    constraint chunks_pkey primary key (id),
    constraint chunks_document_id_fkey foreign key (document_id) references documents (document_id)
  ) tablespace pg_default;