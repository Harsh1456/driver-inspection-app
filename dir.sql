--
-- PostgreSQL database dump
--

-- Dumped from database version 17.5
-- Dumped by pg_dump version 17.5

-- Started on 2026-01-02 19:38:24

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

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 222 (class 1259 OID 100175)
-- Name: inspection_edits; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.inspection_edits (
    id integer NOT NULL,
    file_id character varying(36) NOT NULL,
    signature_data text,
    signature_type character varying(20),
    signer_name character varying(255),
    edited_remarks text,
    original_remarks text,
    edited_at timestamp without time zone,
    signer_role character varying(200),
    signature_date character varying(50)
);


ALTER TABLE public.inspection_edits OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 100174)
-- Name: inspection_edits_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.inspection_edits_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.inspection_edits_id_seq OWNER TO postgres;

--
-- TOC entry 4918 (class 0 OID 0)
-- Dependencies: 221
-- Name: inspection_edits_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.inspection_edits_id_seq OWNED BY public.inspection_edits.id;


--
-- TOC entry 218 (class 1259 OID 99383)
-- Name: report_pages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.report_pages (
    page_id character varying(36) NOT NULL,
    file_id character varying(36) NOT NULL,
    page_number integer NOT NULL,
    has_remarks boolean,
    extracted_text text,
    original_text text,
    correction_applied boolean,
    improvement_score double precision,
    confidence_score double precision,
    image_path character varying(500),
    processed_timestamp timestamp without time zone,
    bounding_boxes text
);


ALTER TABLE public.report_pages OWNER TO postgres;

--
-- TOC entry 217 (class 1259 OID 99376)
-- Name: uploaded_files; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.uploaded_files (
    file_id character varying(36) NOT NULL,
    file_name character varying(255) NOT NULL,
    file_type character varying(10) NOT NULL,
    upload_timestamp timestamp without time zone,
    total_pages integer,
    pages_with_remarks integer,
    pages_without_remarks integer,
    criticality_level character varying(20),
    file_path character varying(500)
);


ALTER TABLE public.uploaded_files OWNER TO postgres;

--
-- TOC entry 220 (class 1259 OID 100161)
-- Name: vehicle_inspections; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vehicle_inspections (
    id integer NOT NULL,
    file_id character varying(36) NOT NULL,
    carrier_name character varying(255),
    location character varying(255),
    inspection_date character varying(50),
    inspection_time character varying(50),
    truck_number character varying(50),
    odometer_reading character varying(50),
    created_at timestamp without time zone
);


ALTER TABLE public.vehicle_inspections OWNER TO postgres;

--
-- TOC entry 219 (class 1259 OID 100160)
-- Name: vehicle_inspections_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.vehicle_inspections_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.vehicle_inspections_id_seq OWNER TO postgres;

--
-- TOC entry 4919 (class 0 OID 0)
-- Dependencies: 219
-- Name: vehicle_inspections_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.vehicle_inspections_id_seq OWNED BY public.vehicle_inspections.id;


--
-- TOC entry 4756 (class 2604 OID 100178)
-- Name: inspection_edits id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inspection_edits ALTER COLUMN id SET DEFAULT nextval('public.inspection_edits_id_seq'::regclass);


--
-- TOC entry 4755 (class 2604 OID 100164)
-- Name: vehicle_inspections id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle_inspections ALTER COLUMN id SET DEFAULT nextval('public.vehicle_inspections_id_seq'::regclass);


--
-- TOC entry 4764 (class 2606 OID 100182)
-- Name: inspection_edits inspection_edits_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inspection_edits
    ADD CONSTRAINT inspection_edits_pkey PRIMARY KEY (id);


--
-- TOC entry 4760 (class 2606 OID 99389)
-- Name: report_pages report_pages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.report_pages
    ADD CONSTRAINT report_pages_pkey PRIMARY KEY (page_id);


--
-- TOC entry 4758 (class 2606 OID 99382)
-- Name: uploaded_files uploaded_files_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.uploaded_files
    ADD CONSTRAINT uploaded_files_pkey PRIMARY KEY (file_id);


--
-- TOC entry 4762 (class 2606 OID 100168)
-- Name: vehicle_inspections vehicle_inspections_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle_inspections
    ADD CONSTRAINT vehicle_inspections_pkey PRIMARY KEY (id);


--
-- TOC entry 4767 (class 2606 OID 100183)
-- Name: inspection_edits inspection_edits_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inspection_edits
    ADD CONSTRAINT inspection_edits_file_id_fkey FOREIGN KEY (file_id) REFERENCES public.uploaded_files(file_id);


--
-- TOC entry 4765 (class 2606 OID 99390)
-- Name: report_pages report_pages_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.report_pages
    ADD CONSTRAINT report_pages_file_id_fkey FOREIGN KEY (file_id) REFERENCES public.uploaded_files(file_id);


--
-- TOC entry 4766 (class 2606 OID 100169)
-- Name: vehicle_inspections vehicle_inspections_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle_inspections
    ADD CONSTRAINT vehicle_inspections_file_id_fkey FOREIGN KEY (file_id) REFERENCES public.uploaded_files(file_id);


-- Completed on 2026-01-02 19:38:24

--
-- PostgreSQL database dump complete
--

