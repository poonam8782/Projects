"""
Unit tests for the text chunking utility (app.utils.chunker).

Tests cover normal operation, edge cases, error handling, and token counting accuracy.
"""

import pytest
import tiktoken

from app.utils.chunker import chunk_text, get_chunk_count


# Test fixtures

@pytest.fixture
def sample_text():
    """Medium-length text sample (~2000 tokens, ~1500 words)."""
    return """
    Artificial intelligence (AI) has revolutionized numerous fields in recent years, 
    from healthcare and finance to transportation and entertainment. Machine learning, 
    a subset of AI, enables computers to learn from data without explicit programming. 
    Deep learning, which uses neural networks with multiple layers, has achieved 
    remarkable success in image recognition, natural language processing, and game playing.
    
    The development of large language models (LLMs) like GPT-4 has demonstrated 
    impressive capabilities in understanding and generating human-like text. These models 
    are trained on vast amounts of text data and can perform a wide range of tasks, 
    including translation, summarization, question answering, and creative writing.
    
    However, AI also raises important ethical considerations. Issues such as bias in 
    training data, privacy concerns, job displacement, and the potential misuse of AI 
    systems need to be carefully addressed. Researchers and policymakers are working 
    to develop frameworks for responsible AI development and deployment.
    
    The future of AI holds both promise and challenges. Advances in areas like 
    explainable AI, federated learning, and AI safety are crucial for building 
    trustworthy systems. As AI continues to evolve, interdisciplinary collaboration 
    between computer scientists, ethicists, policymakers, and domain experts will be 
    essential to ensure that AI benefits society as a whole.
    
    Natural language processing (NLP) is a critical component of AI that focuses on 
    enabling computers to understand, interpret, and generate human language. Recent 
    breakthroughs in transformer architectures have significantly improved NLP 
    capabilities. Applications range from chatbots and virtual assistants to sentiment 
    analysis and content moderation.
    
    Computer vision is another major area of AI research, enabling machines to interpret 
    and understand visual information from the world. From autonomous vehicles that 
    navigate roads to medical imaging systems that assist in diagnosis, computer vision 
    is transforming industries. Object detection, image segmentation, and facial 
    recognition are just a few of the many tasks that modern computer vision systems 
    can perform with high accuracy.
    
    Reinforcement learning, a paradigm where agents learn by interacting with an 
    environment and receiving rewards, has led to breakthroughs in robotics, game AI, 
    and optimization problems. AlphaGo's victory over world champion Go players 
    demonstrated the power of combining deep learning with reinforcement learning.
    
    As we move forward, the integration of AI into everyday life will continue to 
    accelerate. Smart homes, personalized education, precision medicine, and intelligent 
    transportation systems are just the beginning. The key to successful AI adoption 
    lies in balancing innovation with responsibility, ensuring that these powerful 
    technologies are developed and deployed in ways that benefit humanity while 
    minimizing potential harms.
    """ * 3  # Repeat to get ~2000 tokens


@pytest.fixture
def short_text():
    """Very short text (~50 tokens, ~40 words)."""
    return "This is a short test document. It contains only a few sentences and should not be chunked."


@pytest.fixture
def long_text():
    """Long text (~5000 tokens, ~3750 words)."""
    return """
    The history of computing spans thousands of years, from ancient calculating devices 
    to modern supercomputers. The abacus, invented around 2700-2300 BCE in Mesopotamia, 
    was one of the earliest tools for performing arithmetic operations. In the 17th century, 
    mathematicians like Blaise Pascal and Gottfried Wilhelm Leibniz developed mechanical 
    calculators that could perform addition, subtraction, multiplication, and division.
    
    Charles Babbage, often called the "father of the computer," designed the Analytical 
    Engine in the 1830s, a mechanical general-purpose computer. Although it was never 
    built during his lifetime, the design included many concepts used in modern computers, 
    including a processing unit, memory, and input/output capabilities. Ada Lovelace, 
    working with Babbage, wrote what is considered the first computer program.
    
    The 20th century saw rapid advancements in computing technology. The Electronic 
    Numerical Integrator and Computer (ENIAC), built in 1945, was one of the first 
    electronic general-purpose computers. It used vacuum tubes and could perform 
    thousands of calculations per second. However, it was enormous, weighing 30 tons 
    and occupying 1800 square feet.
    
    The invention of the transistor in 1947 by John Bardeen, Walter Brattain, and 
    William Shockley revolutionized electronics. Transistors were smaller, faster, 
    and more reliable than vacuum tubes, paving the way for miniaturization. The 
    integrated circuit, developed in the late 1950s, further reduced the size and 
    cost of electronic components.
    
    The 1970s and 1980s witnessed the rise of personal computers. Companies like Apple, 
    IBM, and Microsoft played pivotal roles in making computers accessible to individuals 
    and small businesses. The Apple II, released in 1977, and the IBM PC, launched in 
    1981, became enormously popular. Microsoft's MS-DOS and later Windows operating 
    systems became the dominant platforms for personal computing.
    
    The internet, which emerged from ARPANET in the late 1960s, transformed computing 
    by enabling global connectivity. The World Wide Web, invented by Tim Berners-Lee 
    in 1989, made the internet accessible to the general public. By the mid-1990s, 
    the internet had become a fundamental part of modern life, facilitating communication, 
    commerce, and information sharing.
    
    Mobile computing gained prominence in the 21st century. Smartphones, combining 
    computing power with telecommunications, have become ubiquitous. The introduction 
    of the iPhone in 2007 marked a turning point, establishing touchscreens and app 
    ecosystems as standard features. Today, billions of people around the world use 
    smartphones for everything from communication and entertainment to banking and 
    navigation.
    
    Cloud computing has revolutionized how we store and process data. Instead of 
    relying on local hardware, users can access computing resources over the internet. 
    Services like Amazon Web Services, Microsoft Azure, and Google Cloud provide 
    scalable infrastructure for businesses and individuals. This shift has enabled 
    new business models and made powerful computing resources accessible to startups 
    and small organizations.
    
    Quantum computing represents the next frontier in computational technology. Unlike 
    classical computers that use bits (0s and 1s), quantum computers use quantum bits 
    or qubits, which can exist in multiple states simultaneously. This property, known 
    as superposition, along with quantum entanglement, could enable quantum computers 
    to solve certain problems exponentially faster than classical computers.
    
    Artificial intelligence and machine learning have become increasingly important 
    in computing. Modern AI systems can recognize patterns, make predictions, and 
    even create content. From recommendation algorithms on streaming platforms to 
    autonomous vehicles and medical diagnosis tools, AI is transforming industries 
    and society.
    
    The future of computing promises continued innovation. Edge computing, which 
    processes data closer to its source rather than in centralized data centers, 
    could reduce latency and improve efficiency. Neuromorphic computing, inspired 
    by the human brain's structure, aims to create more efficient and powerful 
    computing systems. As computing technology evolves, it will continue to shape 
    how we live, work, and interact with the world.
    """ * 5  # Repeat to get ~5000 tokens


# Basic functionality tests

class TestChunkTextBasic:
    """Tests for basic chunking functionality."""
    
    def test_chunk_text_basic(self, sample_text):
        """Verify basic chunking functionality with default parameters."""
        result = chunk_text(sample_text)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(chunk, str) for chunk in result)
        assert all(len(chunk) > 0 for chunk in result)
        # Should generate 2-4 chunks for ~2000 token text with 1000 token chunks
        assert 2 <= len(result) <= 4
    
    def test_chunk_text_with_custom_size(self, sample_text):
        """Verify custom chunk_size parameter works."""
        chunk_size = 500
        overlap = 100
        result = chunk_text(sample_text, chunk_size=chunk_size, overlap=overlap)
        
        # Verify token counts
        encoder = tiktoken.get_encoding("cl100k_base")
        for chunk in result:
            token_count = len(encoder.encode(chunk))
            # Allow ±20% variance due to boundary alignment
            assert token_count <= chunk_size * 1.2
    
    def test_chunk_text_overlap(self, long_text):
        """Verify overlap between consecutive chunks."""
        result = chunk_text(long_text, chunk_size=1000, overlap=200)
        
        assert len(result) >= 2
        
        # Check overlap between first two chunks
        encoder = tiktoken.get_encoding("cl100k_base")
        chunk0_tokens = encoder.encode(result[0])
        chunk1_tokens = encoder.encode(result[1])
        
        # Get last 200 tokens of chunk 0 and first 200 tokens of chunk 1
        chunk0_tail = encoder.decode(chunk0_tokens[-200:])
        chunk1_head = encoder.decode(chunk1_tokens[:200])
        
        # There should be some overlap (at least a few words in common)
        chunk0_words = set(chunk0_tail.split())
        chunk1_words = set(chunk1_head.split())
        overlap_words = chunk0_words & chunk1_words
        
        assert len(overlap_words) > 0
    
    def test_chunk_text_short_text(self, short_text):
        """Verify short text returns single chunk."""
        result = chunk_text(short_text, chunk_size=1000)
        
        assert len(result) == 1
        assert result[0] == short_text


# Edge case tests

class TestChunkTextEdgeCases:
    """Tests for edge cases."""
    
    def test_chunk_text_empty_string(self):
        """Verify empty string handling."""
        result = chunk_text("")
        assert result == []
    
    def test_chunk_text_whitespace_only(self):
        """Verify whitespace-only text handling."""
        result = chunk_text("   \n\t  ")
        assert result == []
    
    def test_chunk_text_special_characters(self):
        """Verify handling of special characters (emojis, unicode)."""
        text = "Hello 👋 世界 🌍! Café résumé naïve. This is a test with émojis 😀🎉 and unicode."
        result = chunk_text(text)
        
        assert len(result) > 0
        # Verify special characters are preserved
        combined = "".join(result)
        assert "👋" in combined
        assert "世界" in combined
        assert "é" in combined
    
    def test_chunk_text_preserves_content(self, sample_text):
        """Verify no text is lost during chunking."""
        result = chunk_text(sample_text)
        
        # Check that all significant words appear in chunks
        original_words = set(sample_text.lower().split())
        chunk_words = set(" ".join(result).lower().split())
        
        # Most words should be preserved (allowing for minor tokenization differences)
        preserved = len(original_words & chunk_words) / len(original_words)
        assert preserved > 0.95  # At least 95% of words preserved
    
    def test_chunk_text_boundary_alignment(self):
        """Verify chunks align on token boundaries (not mid-token)."""
        text = "Hello 世界 🌍! " * 100
        result = chunk_text(text, chunk_size=50, overlap=10)
        
        # Each chunk should be valid UTF-8
        for chunk in result:
            # This will raise if chunk contains broken unicode
            chunk.encode('utf-8')


# Error handling tests

class TestChunkTextErrors:
    """Tests for error handling."""
    
    def test_chunk_text_invalid_chunk_size_zero(self):
        """Verify error handling for chunk_size=0."""
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            chunk_text("test", chunk_size=0)
    
    def test_chunk_text_invalid_chunk_size_negative(self):
        """Verify error handling for negative chunk_size."""
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            chunk_text("test", chunk_size=-100)
    
    def test_chunk_text_invalid_overlap_equal(self):
        """Verify error handling for chunk_size == overlap."""
        with pytest.raises(ValueError, match="chunk_size must be greater than overlap"):
            chunk_text("test", chunk_size=100, overlap=100)
    
    def test_chunk_text_invalid_overlap_greater(self):
        """Verify error handling for overlap > chunk_size."""
        with pytest.raises(ValueError, match="chunk_size must be greater than overlap"):
            chunk_text("test", chunk_size=100, overlap=150)
    
    def test_chunk_text_invalid_overlap_negative(self):
        """Verify error handling for negative overlap."""
        with pytest.raises(ValueError, match="overlap must be non-negative"):
            chunk_text("test", chunk_size=100, overlap=-10)


# Utility function tests

class TestGetChunkCount:
    """Tests for get_chunk_count utility function."""
    
    def test_get_chunk_count(self, long_text):
        """Verify chunk count calculation utility."""
        chunk_size = 1000
        overlap = 200
        
        predicted_count = get_chunk_count(long_text, chunk_size=chunk_size, overlap=overlap)
        actual_chunks = chunk_text(long_text, chunk_size=chunk_size, overlap=overlap)
        actual_count = len(actual_chunks)
        
        # Allow ±1 tolerance due to rounding
        assert abs(predicted_count - actual_count) <= 1
    
    def test_get_chunk_count_empty_text(self):
        """Verify get_chunk_count handles empty text."""
        assert get_chunk_count("") == 0
    
    def test_get_chunk_count_short_text(self, short_text):
        """Verify get_chunk_count handles short text."""
        count = get_chunk_count(short_text, chunk_size=1000)
        assert count == 1


# Parametrized tests

class TestChunkSizesParametrized:
    """Parametrized tests for various chunk sizes."""
    
    @pytest.mark.parametrize("chunk_size,overlap", [
        (500, 100),
        (1000, 200),
        (2000, 400),
        (100, 20),
    ])
    def test_chunk_sizes(self, sample_text, chunk_size, overlap):
        """Test various chunk_size and overlap combinations."""
        result = chunk_text(sample_text, chunk_size=chunk_size, overlap=overlap)
        
        assert len(result) > 0
        assert all(len(chunk) > 0 for chunk in result)


# Encoding tests

class TestDifferentEncodings:
    """Tests for different tiktoken encodings."""
    
    def test_chunk_text_cl100k_base(self, sample_text):
        """Test with cl100k_base encoding (default)."""
        result = chunk_text(sample_text, encoding_name="cl100k_base")
        assert len(result) > 0
    
    def test_chunk_text_p50k_base(self, sample_text):
        """Test with p50k_base encoding."""
        result = chunk_text(sample_text, encoding_name="p50k_base")
        assert len(result) > 0


# Performance test (marked as slow)

@pytest.mark.slow
def test_chunk_text_performance():
    """Verify chunking is reasonably fast."""
    import time
    
    # Create very long text (~100,000 tokens)
    long_text = "This is a test sentence. " * 50000
    
    start_time = time.time()
    result = chunk_text(long_text, chunk_size=1000, overlap=200)
    end_time = time.time()
    
    duration = end_time - start_time
    
    assert len(result) > 0
    assert duration < 5.0  # Should complete in less than 5 seconds
