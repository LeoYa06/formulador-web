--
-- PostgreSQL database dump
--

\restrict nFGAofrLVIV4TV5NCG1srtVYdAkakLgNB91tpRqd7xHaL5HwerOSfhzPBlhg4ep

-- Dumped from database version 17.6 (Debian 17.6-1.pgdg12+1)
-- Dumped by pg_dump version 17.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: formulador_db_user
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO formulador_db_user;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: base_ingredients; Type: TABLE; Schema: public; Owner: formulador_db_user
--

CREATE TABLE public.base_ingredients (
    id integer NOT NULL,
    name text NOT NULL,
    protein_percent real,
    fat_percent real,
    water_percent real,
    "Ve_Protein_Percent" real,
    notes text,
    water_retention_factor real,
    min_usage_percent real,
    max_usage_percent real,
    precio_por_kg real,
    categoria text
);


ALTER TABLE public.base_ingredients OWNER TO formulador_db_user;

--
-- Name: bibliografia; Type: TABLE; Schema: public; Owner: formulador_db_user
--

CREATE TABLE public.bibliografia (
    id integer NOT NULL,
    titulo text NOT NULL,
    tipo text,
    contenido text NOT NULL
);


ALTER TABLE public.bibliografia OWNER TO formulador_db_user;

--
-- Name: bibliografia_id_seq; Type: SEQUENCE; Schema: public; Owner: formulador_db_user
--

CREATE SEQUENCE public.bibliografia_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bibliografia_id_seq OWNER TO formulador_db_user;

--
-- Name: bibliografia_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: formulador_db_user
--

ALTER SEQUENCE public.bibliografia_id_seq OWNED BY public.bibliografia.id;


--
-- Name: formula_ingredients; Type: TABLE; Schema: public; Owner: formulador_db_user
--

CREATE TABLE public.formula_ingredients (
    id integer NOT NULL,
    formula_id integer NOT NULL,
    ingredient_id integer NOT NULL,
    quantity real NOT NULL,
    unit text NOT NULL
);


ALTER TABLE public.formula_ingredients OWNER TO formulador_db_user;

--
-- Name: formula_ingredients_id_seq; Type: SEQUENCE; Schema: public; Owner: formulador_db_user
--

CREATE SEQUENCE public.formula_ingredients_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.formula_ingredients_id_seq OWNER TO formulador_db_user;

--
-- Name: formula_ingredients_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: formulador_db_user
--

ALTER SEQUENCE public.formula_ingredients_id_seq OWNED BY public.formula_ingredients.id;


--
-- Name: formulas; Type: TABLE; Schema: public; Owner: formulador_db_user
--

CREATE TABLE public.formulas (
    id integer NOT NULL,
    product_name text NOT NULL,
    description text,
    creation_date text NOT NULL,
    user_id integer
);


ALTER TABLE public.formulas OWNER TO formulador_db_user;

--
-- Name: formulas_id_seq; Type: SEQUENCE; Schema: public; Owner: formulador_db_user
--

CREATE SEQUENCE public.formulas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.formulas_id_seq OWNER TO formulador_db_user;

--
-- Name: formulas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: formulador_db_user
--

ALTER SEQUENCE public.formulas_id_seq OWNED BY public.formulas.id;


--
-- Name: ingredients_id_seq; Type: SEQUENCE; Schema: public; Owner: formulador_db_user
--

CREATE SEQUENCE public.ingredients_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ingredients_id_seq OWNER TO formulador_db_user;

--
-- Name: ingredients_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: formulador_db_user
--

ALTER SEQUENCE public.ingredients_id_seq OWNED BY public.base_ingredients.id;


--
-- Name: user_ingredients; Type: TABLE; Schema: public; Owner: formulador_db_user
--

CREATE TABLE public.user_ingredients (
    id integer NOT NULL,
    name text NOT NULL,
    protein_percent real,
    fat_percent real,
    water_percent real,
    ve_protein_percent real,
    notes text,
    water_retention_factor real,
    min_usage_percent real,
    max_usage_percent real,
    precio_por_kg real,
    categoria text,
    user_id integer NOT NULL
);


ALTER TABLE public.user_ingredients OWNER TO formulador_db_user;

--
-- Name: user_ingredients_id_seq; Type: SEQUENCE; Schema: public; Owner: formulador_db_user
--

CREATE SEQUENCE public.user_ingredients_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_ingredients_id_seq OWNER TO formulador_db_user;

--
-- Name: user_ingredients_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: formulador_db_user
--

ALTER SEQUENCE public.user_ingredients_id_seq OWNED BY public.user_ingredients.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: formulador_db_user
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username text NOT NULL,
    password_hash text NOT NULL,
    full_name text,
    is_verified boolean DEFAULT false,
    verification_code character varying(6),
    code_expiry timestamp without time zone,
    session_token character varying(64)
);


ALTER TABLE public.users OWNER TO formulador_db_user;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: formulador_db_user
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO formulador_db_user;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: formulador_db_user
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: base_ingredients id; Type: DEFAULT; Schema: public; Owner: formulador_db_user
--

ALTER TABLE ONLY public.base_ingredients ALTER COLUMN id SET DEFAULT nextval('public.ingredients_id_seq'::regclass);


--
-- Name: bibliografia id; Type: DEFAULT; Schema: public; Owner: formulador_db_user
--

ALTER TABLE ONLY public.bibliografia ALTER COLUMN id SET DEFAULT nextval('public.bibliografia_id_seq'::regclass);


--
-- Name: formula_ingredients id; Type: DEFAULT; Schema: public; Owner: formulador_db_user
--

ALTER TABLE ONLY public.formula_ingredients ALTER COLUMN id SET DEFAULT nextval('public.formula_ingredients_id_seq'::regclass);


--
-- Name: formulas id; Type: DEFAULT; Schema: public; Owner: formulador_db_user
--

ALTER TABLE ONLY public.formulas ALTER COLUMN id SET DEFAULT nextval('public.formulas_id_seq'::regclass);


--
-- Name: user_ingredients id; Type: DEFAULT; Schema: public; Owner: formulador_db_user
--

ALTER TABLE ONLY public.user_ingredients ALTER COLUMN id SET DEFAULT nextval('public.user_ingredients_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: formulador_db_user
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: bibliografia bibliografia_pkey; Type: CONSTRAINT; Schema: public; Owner: formulador_db_user
--

ALTER TABLE ONLY public.bibliografia
    ADD CONSTRAINT bibliografia_pkey PRIMARY KEY (id);


--
-- Name: formula_ingredients formula_ingredients_pkey; Type: CONSTRAINT; Schema: public; Owner: formulador_db_user
--

ALTER TABLE ONLY public.formula_ingredients
    ADD CONSTRAINT formula_ingredients_pkey PRIMARY KEY (id);


--
-- Name: formulas formulas_pkey; Type: CONSTRAINT; Schema: public; Owner: formulador_db_user
--

ALTER TABLE ONLY public.formulas
    ADD CONSTRAINT formulas_pkey PRIMARY KEY (id);


--
-- Name: base_ingredients ingredients_name_key; Type: CONSTRAINT; Schema: public; Owner: formulador_db_user
--

ALTER TABLE ONLY public.base_ingredients
    ADD CONSTRAINT ingredients_name_key UNIQUE (name);


--
-- Name: base_ingredients ingredients_pkey; Type: CONSTRAINT; Schema: public; Owner: formulador_db_user
--

ALTER TABLE ONLY public.base_ingredients
    ADD CONSTRAINT ingredients_pkey PRIMARY KEY (id);


--
-- Name: formulas unique_user_product; Type: CONSTRAINT; Schema: public; Owner: formulador_db_user
--

ALTER TABLE ONLY public.formulas
    ADD CONSTRAINT unique_user_product UNIQUE (user_id, product_name);


--
-- Name: user_ingredients user_ingredients_pkey; Type: CONSTRAINT; Schema: public; Owner: formulador_db_user
--

ALTER TABLE ONLY public.user_ingredients
    ADD CONSTRAINT user_ingredients_pkey PRIMARY KEY (id);


--
-- Name: user_ingredients user_ingredients_user_id_name_key; Type: CONSTRAINT; Schema: public; Owner: formulador_db_user
--

ALTER TABLE ONLY public.user_ingredients
    ADD CONSTRAINT user_ingredients_user_id_name_key UNIQUE (user_id, name);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: formulador_db_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: formulador_db_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: formula_ingredients formula_ingredients_formula_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: formulador_db_user
--

ALTER TABLE ONLY public.formula_ingredients
    ADD CONSTRAINT formula_ingredients_formula_id_fkey FOREIGN KEY (formula_id) REFERENCES public.formulas(id) ON DELETE CASCADE;


--
-- Name: formulas formulas_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: formulador_db_user
--

ALTER TABLE ONLY public.formulas
    ADD CONSTRAINT formulas_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_ingredients user_ingredients_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: formulador_db_user
--

ALTER TABLE ONLY public.user_ingredients
    ADD CONSTRAINT user_ingredients_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: -; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres GRANT ALL ON SEQUENCES TO formulador_db_user;


--
-- Name: DEFAULT PRIVILEGES FOR TYPES; Type: DEFAULT ACL; Schema: -; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres GRANT ALL ON TYPES TO formulador_db_user;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: -; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres GRANT ALL ON FUNCTIONS TO formulador_db_user;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: -; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres GRANT ALL ON TABLES TO formulador_db_user;


--
-- PostgreSQL database dump complete
--

\unrestrict nFGAofrLVIV4TV5NCG1srtVYdAkakLgNB91tpRqd7xHaL5HwerOSfhzPBlhg4ep

